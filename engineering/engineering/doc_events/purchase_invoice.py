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
    #     create_purchase_invoice(self)
    # except Exception as e:
    #     frappe.db.rollback()
    #     frappe.throw(_("Purchase Invoice Exception: " + e))
    # else:
    #     frappe.db.commit()
    pass
    # create_purchase_invoice(self)

def on_cancel(self, method):
    pass

def on_trash(self, method):
    pass


def create_purchase_invoice(self):
    authority = frappe.db.get_value("Company", self.company, "authority")
    
    def get_purchase_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
        def set_missing_value(source, target):
            try:
                alternate_supplier = frappe.db.get_value("Company", source.supplier, "alternate_company")
            except:
                alternate_supplier = None
            
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
            
            if source.credit_to:
                target.credit_to = source.credit_to.replace(source_company_abbr, target_company_abbr)
            
            if source.taxes_and_charges:
                target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

                for index, i in enumerate(source.taxes):
                    target.taxes[index].charge_type = "Actual"
                    target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)

            if self.amended_from:
                name = frappe.db.get_value("Purchase Invoice", {"ref_invoice": source.amended_from}, "name")
                target.amended_from = name
            
            if alternate_supplier:
                target.supplier = alternate_supplier
            
            target.run_method('set_missing_values')
        
        def update_accounts(source_doc, target_doc, source_parent):
            target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

            doc = frappe.get_doc("Company", target_company)

            target_doc.income_account = doc.default_income_account
            target_doc.expense_account = doc.default_expense_account
            target_doc.cost_center = doc.cost_center
            
            if source_doc.pr_ref:
                target_doc.pr_detail = source_doc.pr_ref
            
            if source_doc.po_ref:
                target_doc.po_detail = source_doc.po_ref
            
            if source_doc.po_doc_ref:
                target_doc.purchase_order = source_doc.po_doc_ref
            
            if source_doc.pr_doc_ref:
                target_doc.purchase_receipt = source_doc.pr_doc_ref

            if source_doc.warehouse:
                target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
            
            if source_doc.rejected_warehouse:
                target_doc.rejected_warehouse = source_doc.rejected_warehouse.replace(source_company_abbr, target_company_abbr)
        
        fields = {
            "Purchase Invoice": {
                "doctype": "Purchase Invoice",
                "field_map": {
                    "ref_invoice": "name",
                },
                "field_no_map":{
                    "authority",
                }
            },
            "Purchase Invoice Item": {
                "doctype": "Purchase Invoice Item",
                "field_map": {
                    "item_design": "item_code",
                    "item_code": "item_design",
                    # Rate
                    "full_rate": "rate",
                    "rate": "discounted_rate",
                    # Quantity
                    "full_qty": "qty",
                    "received_full_qty": "received_qty",
                    "rejected_full_qty": "rejected_qty",
                    "qty": "real_qty",
                    "received_real_qty": "received_full_qty",
                    "rejected_real_qty": "rejected_full_qty",
                    # Ref Links
                    "purchase_receipt_docname": "purchase_receipt",
                    "purchase_receipt_childname": "pr_detail",
                    "po_docname": "purchase_order",
                    "po_childname": "po_detail",
                },
                "field_no_map": {
                    "full_rate",
                    "full_qty",
                    "series",
                },
                "postprocess": update_accounts,
            }
        }
        doclist = get_mapped_doc(
            "Purchase Invoice",
            source_name,
            fields,
            target_doc,
            set_missing_value,
            ignore_permissions=ignore_permissions
        )

        return doclist

    if authority == "Authorized":
        
        pi = get_purchase_invoice_entry(self.name)
        frappe.msgprint(pi.company)
        pi.save(ignore_permissions= True)
        self.db_set('ref_invoice', pi.name)
        pi.submit()
        
