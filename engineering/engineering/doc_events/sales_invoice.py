# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import make_inter_company_transaction


def validate(self, method):
    pass

def on_submit(self, method):
    # try:
    #     create_sales_invoice(self)
    #     create_purchase_invoice(self)
    # except Exception as e:
    #     frappe.db.rollback()
    #     frappe.throw(_("Sales Invoice Exception: " + e))
    # else:
    #     frappe.db.commit()
    # create_purchase_invoice(self)
    create_sales_invoice(self)
    create_purchase_invoice(self)

def on_cancel(self, method):
    try:
        cancel_purchase_invoice(self)
        cancel_main_sales_invoice(self)
    except Exception as e:
        frappe.db.rollback()
        frappe.throw(e)
    else:
        frappe.db.commit()

def on_trash(self, method):
    delete_main_sales_invoice(self)
    delete_purchase_invoice(self)


def create_sales_invoice(self):
    authority = frappe.db.get_value("Company", self.company, "authority")
    def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
        def set_missing_value(source, target):
            try:
                alternate_customer = frappe.db.get_value("Company", source.customer, "alternate_company")
            except:
                alternate_customer = None
            
            target_company = frappe.db.get_value("Company", source.company, "alternate_company")
            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

            target.company = target_company
            target.ref_invoice = self.name
            target.authority = "Unauthorized"

            for index, i in enumerate(source.items):
                if source.items[index].net_rate:
                    if source.items[index].net_rate != source.items[index].rate:
                        full_amount = source.items[index].full_qty * source.items[index].full_rate
                        amount_diff = source.items[index].amount - source.items[index].net_amount

                        target.items[index].rate = (full_amount - amount_diff) / source.items[index].full_qty
            
            if source.debit_to:
                target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
            
            if source.taxes_and_charges:
                target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

                for index, i in enumerate(source.taxes):
                    target.taxes[index].charge_type = "Actual"
                    target.taxes[index].included_in_print_rate = 0
                    target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
            
            if self.amended_from:
                name = frappe.db.get_value("Sales Invoice", {"ref_invoice": source.amended_from}, "name")
                target.amended_from = name
            
            if alternate_customer:
                target.customer = alternate_customer
            
            target.run_method('set_missing_values')
        
        def update_accounts(source_doc, target_doc, source_parent):
            target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

            doc = frappe.get_doc("Company", target_company)

            target_doc.income_account = doc.default_income_account
            target_doc.expense_account = doc.default_expense_account
            target_doc.cost_center = doc.cost_center
        
        fields = {
            "Sales Invoice": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "ref_invoice": "name",
                },
                "field_no_map":{
                    "authority",
                },
            },
            "Sales Invoice Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_variant": "item_code",
                    "item_code": "item_variant",
                    "full_rate": "rate",
                    "full_qty": "qty",
                    "rate": "discounted_rate",
                    "qty": "real_qty",
                    "delivery_docname": "delivery_note",
                    "delivery_childname": "dn_detail",
                    "so_docname": "sales_order",
                    "so_childname": "so_detail",
                    "pr_ref": "pr_detail",
                    "po_ref": "purchase_order_item",
                },
                "field_no_map": {
                    "full_rate",
                    "full_qty",
                    "series",
                },
                "postprocess": update_accounts,
            },
        }

        doclist = get_mapped_doc(
            "Sales Invoice",
            source_name,
            fields,
            target_doc,
            set_missing_value,
            ignore_permissions=ignore_permissions
        )

        return doclist
    
    if authority == "Authorized":
        si = get_sales_invoice_entry(self.name)
        si.save(ignore_permissions = True)

        self.db_set('ref_invoice', si.name)
        si.submit() 

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
                    "purchase_order_item": "po_detail",
                    "item_varient": "item_design"
                }

                pi = make_inter_company_transaction(
                    self,
                    "Sales Invoice",
                    "Purchase Invoice",
                    "sales_invoice",
                    field_map = field_map,
                    child_field_map = child_field_map
                )

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


def cancel_main_sales_invoice(self):
    if self.ref_invoice:
        si = frappe.get_doc("Sales Invoice", {'ref_invoice':self.name})
    else:
        si = None
    
    if si:
        if si.docstatus == 1:
            si.flags.ignore_permissions = True
            si.cancel()


def cancel_purchase_invoice(self):
    if self.purchase_invoice:
        pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
    else:
        pi = None

    if pi:
        if pi.docstatus == 1:
            pi.flags.ignore_permissions = True
            pi.cancel()

def delete_purchase_invoice(self):
    if self.purchase_invoice:
        frappe.db.set_value("Purchase Invoice", self.purchase_invoice, 'sales_invoice', '')    
        frappe.db.set_value("Purchase Invoice", self.purchase_invoice, 'inter_company_invoice_reference', '')
        frappe.db.set_value("Sales Invoice", self.name, 'purchase_invoice', '')    
        frappe.db.set_value("Sales Invoice", self.name, 'inter_company_invoice_reference', '')
        frappe.delete_doc("Purchase Invoice", self.purchase_invoice, force = 1, ignore_permissions=True)  

def delete_main_sales_invoice(self):
    if self.ref_invoice:
        frappe.db.set_value("Sales Invoice", self.name, 'ref_invoice', '')    
        frappe.db.set_value("Sales Invoice", self.ref_invoice, 'ref_invoice', '') 
        frappe.delete_doc("Sales Invoice", self.ref_invoice, force = 1, ignore_permissions=True)