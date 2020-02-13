import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import get_url_to_form
from engineering.api import make_inter_company_transaction

def on_submit(self, method):
    """Custom On Submit Fuction"""
    create_purchase_receipt(self)
    change_delivery_authority(self.name)

def on_cancel(self, method):
    cancel_purchase_receipt(self)

def on_trash(self, method):
    delete_purchase_receipt(self)

def delete_purchase_receipt(self):
    try:
        check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
    except:
        check_inter_company_transaction = None
    
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            company = frappe.get_doc("Company", self.customer)
            inter_company_list = [item.company for item in company.allowed_to_transact_with]
            
            try:
                frappe.db.set_value("Delivery Note", self.name, 'inter_company_receipt_reference', '')
                frappe.db.set_value("Purchase Receipt", self.inter_company_receipt_reference, 'inter_company_delivery_reference', '')
                
                frappe.delete_doc("Purchase Receipt", self.inter_company_receipt_reference, force = 1, ignore_permissions=True)
                frappe.msgprint(_("Purchase Order <b>{name}</b> has been deleted!".format(name=self.inter_company_receipt_reference)), title="Purchase Order Deleted", indicator="red")
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)
            else:
                frappe.db.commit()

def cancel_purchase_receipt(self):
    try:
        check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
    except:
        check_inter_company_transaction = None
    
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            company = frappe.get_doc("Company", self.customer)
            inter_company_list = [item.company for item in company.allowed_to_transact_with]
            
            if self.company in inter_company_list:
                try:
                    pr = frappe.get_doc("Purchase Receipt", self.inter_company_receipt_reference)
                    pr.flags.ignore_permissions = True
                    pr.cancel()

                    url = get_url_to_form("Purchase Receipt", pr.name)
                    frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=pr.name)), title="Purchase Receipt Cancelled", indicator="red")
                except:
                    pass
                
def create_purchase_receipt(self):
    try:
        check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
    except:
        check_inter_company_transaction = None
    
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            company = frappe.get_doc("Company", self.customer)
            inter_company_list = [item.company for item in company.allowed_to_transact_with]

            if self.company in inter_company_list:
                field_map = {
                    "name": "supplier_delivery_note",
                }
                child_field_map = {
                    "purchase_order_item": "purchase_order_item",
                }
                pr = make_inter_company_transaction(self, "Delivery Note", "Purchase Receipt", "inter_company_delivery_reference", field_map=field_map, child_field_map = child_field_map)

                try:
                    pr.save(ignore_permissions = True)
                    for index, item in enumerate(self.items):
                        against_sales_order = self.items[index].against_sales_order
                        try:
                            purchase_order = frappe.db.get_value("Sales Order", against_sales_order, 'inter_company_order_reference')
                        except:
                            purchase_order = None
                            
                        if purchase_order:
                            schedule_date = frappe.db.get_value("Purchase Order", purchase_order, 'schedule_date')
                            pr.items[index].purchase_order = purchase_order
                            pr.items[index].schedule_date = schedule_date
                            frappe.db.set_value("Delivery Note Item", self.items[index].name, 'pr_detail', pr.items[index].name)
                    
                    pr.save(ignore_permissions = True)

                    frappe.db.set_value("Delivery Note", self.name, 'inter_company_receipt_reference', pr.name)
                    frappe.db.set_value("Purchase Receipt", pr.name, 'inter_company_delivery_reference', self.name)
                    frappe.db.set_value("Purchase Receipt", pr.name, 'supplier_delivery_note', self.name)

                    url = get_url_to_form("Purchase Receipt", pr.name)
                    frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully! Please submit the Purchase Recipient".format(url=url, name=pr.name)), title="Purchase Receipt Created", indicator="green")
                except Exception as e:
                    frappe.db.rollback()
                    frappe.throw(e)
                else:
                    frappe.db.commit()

def change_delivery_authority(name):
    """Function to change authorty of Delivery Note"""

    status = frappe.get_value("Delivery Note", name, "status")
    
    if status == 'Completed':
        frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
    else:
        frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
    
    frappe.db.commit()
