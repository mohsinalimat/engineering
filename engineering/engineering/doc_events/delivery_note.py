import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address


def get_invoiced_qty_map(delivery_note):
    """returns a map: {dn_detail: invoiced_qty}"""

    invoiced_qty_map = {}

    for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
        where delivery_note=%s and docstatus=1""", delivery_note):
            if not invoiced_qty_map.get(dn_detail):
                invoiced_qty_map[dn_detail] = 0
            invoiced_qty_map[dn_detail] += qty

    return invoiced_qty_map

def get_returned_qty_map(delivery_note):
    """returns a map: {so_detail: returned_qty}"""

    returned_qty_map = frappe._dict(frappe.db.sql("""select dn_item.item_code, sum(abs(dn_item.qty)) as qty
        from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
        where dn.name = dn_item.parent
            and dn.docstatus = 1
            and dn.is_return = 1
            and dn.return_against = %s
        group by dn_item.item_code
    """, delivery_note))

    return returned_qty_map

def change_delivery_authority(name):
    """Function to change authorty of Delivery Note"""

    status = frappe.get_value("Delivery Note", name, "status")
    
    if status == 'Completed':
        frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
    else:
        frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
    
    frappe.db.commit()


@frappe.whitelist()
def on_submit(self, test):
    """Custom On Submit Fuction"""
    # frappe.throw("Maki")
    change_delivery_authority(self.name)
    # create_purchase_receipt(self)

def create_purchase_receipt(self):
    check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            pr = make_inter_company_transaction(self, "Purchase Order", self.name)

            try:
                pr.save(ignore_permissions = True)
                pr.submit()
                frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_no', so.name)
                frappe.db.set_value('Purchase Order', self.name, 'sales_order', so.name)
                frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_date', so.transaction_date)
                
                url = get_url_to_form("Sales Order", so.name)
                frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=so.name)), title="Sales Order Cancelled", indicator="green")

            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)
            else:
                frappe.db.commit()


@frappe.whitelist()
def create_invoice(source_name, target_doc=None):
    doc = frappe.get_doc('Delivery Note', source_name)

    to_make_invoice_qty_map = {}
    returned_qty_map = get_returned_qty_map(source_name)
    invoiced_qty_map = get_invoiced_qty_map(source_name)

    def set_missing_values(source, target):
        target.is_pos = 0
        target.ignore_pricing_rule = 1
        target.run_method("set_missing_values")
        target.run_method("set_po_nos")
        alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")
        target.expense_account = ""

        if alternate_company:
            target.company = alternate_company

        if len(target.get("items")) == 0:
            frappe.throw(_("All these items have already been invoiced"))

        target.run_method("calculate_taxes_and_totals")

        if source.company_address:
            target.update({'company_address': source.company_address})
        else:
            target.update(get_company_address(target.company))

        if target.company_address:
            target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))


    def get_pending_qty(item_row):
        pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

        returned_qty = 0
        if returned_qty_map.get(item_row.item_code, 0) > 0:
            returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
            returned_qty_map[item_row.item_code] -= pending_qty

        if returned_qty:
            if returned_qty >= pending_qty:
                pending_qty = 0
                returned_qty -= pending_qty
            else:
                pending_qty -= returned_qty
                returned_qty = 0

        to_make_invoice_qty_map[item_row.name] = pending_qty

        return pending_qty
    
    def update_acoounts(source_doc, target_doc, source_parent):
        target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

        doc = frappe.get_doc("Company", target_company)

        target_doc.income_account = doc.default_income_account
        target_doc.expense_account = doc.default_expense_account
        target_doc.cost_center = doc.cost_center

    fields = {
        "Delivery Note": {
            "doctype": "Sales Invoice",
            "field_map": {
                "is_return": "is_return"
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        },
        "Delivery Note Item": {
            "doctype": "Sales Invoice Item",
            "field_map": {
                "item_code": "item_variant",
                "item_series": "item_code",
                "parent": "delivery_docname",
                "name":"delivery_childname",
                "so_detail": "so_childname" ,
                "against_sales_order": "so_docname",
                "serial_no": "serial_no",
                "real_qty": "qty",
                "discounted_rate": "rate",
                "qty": "full_qty",
                "rate":"full_rate",
            },
            "field_no_map": [
                "income_account",
                "expense_account",
                "cost_center",
                "warehouse",
                "real_qty",
                "discounted_rate",
            ],
            "postprocess": update_acoounts,
            "filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
        },
        "Sales Team": {
            "doctype": "Sales Team",
            "field_map": {
                "incentives": "incentives"
            },
            "add_if_empty": True
        }
    }

    doc = get_mapped_doc(
        "Delivery Note",
        source_name,
        fields,
        target_doc,
        set_missing_values
    )

    return doc


@frappe.whitelist()
def make_inter_company_purchase_receipt(source_name, target_doc=None):
    return make_inter_company_transaction("Delivery Note", source_name, target_doc)

def get_inter_company_details(doc, doctype):
    if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"]:
        party = frappe.db.get_value("Supplier", {"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company}, "name")
        company = frappe.get_cached_value("Customer", doc.customer, "represents_company")
    else:
        party = frappe.db.get_value("Customer", {"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company}, "name")
        company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

    return {
        "party": party,
        "company": company
    }

def validate_inter_company_transaction(doc, doctype):

    details = get_inter_company_details(doc, doctype)
    price_list = doc.selling_price_list if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"] else doc.buying_price_list
    valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
    if not valid_price_list:
        frappe.throw(_("Selected Price List should have buying and selling fields checked."))

    party = details.get("party")
    if not party:
        partytype = "Supplier" if doctype in ["Sales Invoice", "Sales Order", "Delivery Note"] else "Customer"
        frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

    company = details.get("company")
    default_currency = frappe.get_cached_value('Company', company, "default_currency")
    if default_currency != doc.currency:
        frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))

    return

def make_inter_company_transaction(doctype, source_name, target_doc=None):
    if doctype in ["Delivery Note", "Purchase Receipt"]:
        source_doc = frappe.get_doc(doctype, source_name)
        target_doctype = "Purchase Receipt"

        validate_inter_company_transaction(source_doc, doctype)
        details = get_inter_company_details(source_doc, doctype)

        def set_missing_values(source, target):
            target.run_method("set_missing_values")

        def update_details(source_doc, target_doc, source_parent):
            target_doc.inter_company_invoice_reference = source_doc.name
            if target_doc.doctype in ["Purchase Invoice", "Purchase Order", "Purchase Receipt"]:
                target_doc.company = details.get("company")
                target_doc.supplier = details.get("party")
                target_doc.buying_price_list = source_doc.selling_price_list
            else:
                target_doc.company = details.get("company")
                target_doc.customer = details.get("party")
                target_doc.buying_price_list = source_doc.selling_price_list

        doclist = get_mapped_doc(doctype, source_name,	{
            doctype: {
                "doctype": target_doctype,
                "postprocess": update_details,
                "field_no_map": [
                    "taxes_and_charges"
                ]
            },
            doctype +" Item": {
                "doctype": target_doctype + " Item",
                "field_no_map": [
                    "income_account",
                    "expense_account",
                    "cost_center",
                    "warehouse"
                ]
            }

        }, target_doc, set_missing_values)

        return doclist