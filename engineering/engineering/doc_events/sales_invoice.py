import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from engineering.api import make_inter_company_transaction
from frappe.utils import get_url_to_form

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    create_main_sales_invoice(self)
    create_purchase_invoice(self)

def on_cancel(self, test):
    """On Cancel Custom Function for Sales Invoice"""
    # cancel_main_sales_invoice(self)
    pass

def on_trash(self, test):
    # delete_sales_invoice(self)
    pass

def change_delivery_authority(name):
    dn_status = frappe.get_value("Delivery Note", name, "status")
    if dn_status == 'Completed':
        frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
    else:
        frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
    
    frappe.db.commit()

def create_sales_invoice(self):
    pass

def create_purchase_invoice(self):
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
                    "name": "bill_no",
                    "posting_date": "bill_date",
                }
                child_field_map = {
                    "pr_detail": "pr_detail",
                    "purchase_order_item": "po_detail"
                }

                pi = make_inter_company_transaction(self, "Sales Invoice", "Purchase Invoice", "purchase_invoice", field_map=field_map, child_field_map = child_field_map)
                
                try:
                    for index, item in enumerate(self.items):
                        delivery_note = self.items[index].delivery_note
                        
                        sales_order = self.items[index].sales_order
                        try:
                            purchase_receipt = frappe.db.get_value("Delivery Note", delivery_note, 'inter_company_receipt_reference')
                        except:
                            purchase_receipt = None
                        
                        try:
                            purchase_order = frappe.db.get_value("Sales Order", sales_order, 'inter_company_order_reference')
                        except:
                            purchase_order = None
                        
                        if purchase_receipt:
                            pi.items[index].purchase_receipt = purchase_receipt
                        
                        if purchase_order:
                            pi.items[index].purchase_order = purchase_order
                             
                    pi.save(ignore_permissions = True)
                    
                    pi.submit()
                    
                    frappe.db.set_value("Sales Invoice", self.name, 'inter_company_invoice_reference', pi.name)
                    frappe.db.set_value("Sales Invoice", self.name, 'purchase_invoice', pi.name)
                    
                    frappe.db.set_value("Purchase Invoice", pi.name, 'inter_company_invoice_reference', self.name)
                    frappe.db.set_value("Purchase Invoice", pi.name, 'sales_invoice', self.name)
                    
                    url = get_url_to_form("Purchase Invoice", pi.name)
                    frappe.msgprint(_("Purchase Invoice <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=pi.name)), title="Purchase Invoice Created", indicator="green")
                except Exception as e:
                    frappe.db.rollback()
                    frappe.throw(e)
                else:
                    frappe.db.commit()

def create_main_sales_invoice(self)
    pass