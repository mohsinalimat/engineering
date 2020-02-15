import frappe

from frappe.utils import flt, cint, nowdate

from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address

def get_invoiced_qty_map(purchase_receipt):
    """returns a map: {pr_detail: invoiced_qty}"""
    invoiced_qty_map = {}

    for pr_detail, qty in frappe.db.sql("""select pr_detail, qty from `tabPurchase Invoice Item`
        where purchase_receipt=%s and docstatus=1""", purchase_receipt):
            if not invoiced_qty_map.get(pr_detail):
                invoiced_qty_map[pr_detail] = 0
            invoiced_qty_map[pr_detail] += qty

    return invoiced_qty_map

def get_returned_qty_map(purchase_receipt):
    """returns a map: {so_detail: returned_qty}"""
    returned_qty_map = frappe._dict(frappe.db.sql("""select pr_item.item_code, sum(abs(pr_item.qty)) as qty
        from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
        where pr.name = pr_item.parent
            and pr.docstatus = 1
            and pr.is_return = 1
            and pr.return_against = %s
        group by pr_item.item_code
    """, purchase_receipt))

    return returned_qty_map

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
    doc = frappe.get_doc('Purchase Receipt', source_name)
    returned_qty_map = get_returned_qty_map(source_name)
    invoiced_qty_map = get_invoiced_qty_map(source_name)

    def set_missing_values(source, target):
        if len(target.get("items")) == 0:
            frappe.throw(_("All items have already been invoiced"))

        doc = frappe.get_doc(target)
        doc.ignore_pricing_rule = 1
        doc.run_method("onload")
        doc.run_method("set_missing_values")
        doc.run_method("calculate_taxes_and_totals")

        target.expense_account = ""

        alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")

        if alternate_company:
            target.company = alternate_company

    def update_item(source_doc, target_doc, source_parent):
        target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

        target_doc.company = target_company
        target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
        source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

        doc = frappe.get_doc("Company", target_company)
        
        target_doc.income_account = doc.default_income_account
        target_doc.expense_account = doc.default_expense_account
        target_doc.cost_center = doc.cost_center
        target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)

    def get_pending_qty(item_row):
        pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)
        returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
        if returned_qty:
            if returned_qty >= pending_qty:
                pending_qty = 0
                returned_qty -= pending_qty
            else:
                pending_qty -= returned_qty
                returned_qty = 0
        return pending_qty, returned_qty


    doclist = get_mapped_doc("Purchase Receipt", source_name,	{
        "Purchase Receipt": {
            "doctype": "Purchase Invoice",
            "field_map": {
                "is_return": "is_return"
            },
            "validation": {
                "docstatus": ["=", 1],
            },
        },
        "Purchase Receipt Item": {
            "doctype": "Purchase Invoice Item",
            "field_map": {
                "item_code": "item_varient",
                "item_varient": "item_code",
                "parent": "purchase_receipt_docname",
                "name":"purchase_receipt_childname",
                "purchase_order_item": "pr_childname",
                "purchase_order": "pr_doctype",
                "is_fixed_asset": "is_fixed_asset",
                "asset_location": "asset_location",
                "asset_category": 'asset_category',
                # Rate
                "discounted_rate": "rate",
                "rate":"full_rate",
                # Quantity
                "real_qty": "qty",
                "received_real_qty": "received_qty",
                "rejected_real_qty": "rejected_qty",
                "qty": "full_qty",
                "received_qty": "received_full_qty",
                "rejected_qty": "rejected_full_qty",
                "purchase_order": "po_docname",
                "purchase_order_item": "po_childname"
            },
            "field_no_map": [
                "income_account",
                "expense_account",
                "cost_center",
                "warehouse",
                "discounted_rate",
                "received_real_qty",
                "real_qty",
                "rejected_real_qty",
            ],
            "postprocess": update_item,
        }
    }, target_doc, set_missing_values)

    return doclist

@frappe.whitelist()
def make_inter_company_delivery_note(source_name, target_doc=None):
    return make_inter_company_transaction("Purchase Receipt", source_name, target_doc)

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
        target_doctype = "Delivery Note"

        validate_inter_company_transaction(source_doc, doctype)
        details = get_inter_company_details(source_doc, doctype)

        def set_missing_values(source, target):
            target.run_method("set_missing_values")

        def update_details(source_doc, target_doc, source_parent):
            target_doc.inter_company_invoice_reference = source_doc.name
            if target_doc.doctype in ["Purchase Invoice", "Purchase Order", "Purchase Receipt"]:
                target_doc.company = details.get("company")
                target_doc.supplier = details.get("party")
                target_doc.selling_price_list = source_doc.buying_price_list
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