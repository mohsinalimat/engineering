# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz Tech Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_inter_company_details, validate_inter_company_transaction
from frappe.utils import nowdate, get_url_to_form, flt, cstr, getdate, get_fullname, now_datetime, parse_val, add_years


def on_submit(self, method):
    create_sales_order(self)

def on_cancel(self, method):
    cancel_sales_order(self)

def cancel_sales_order(self):
    check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            if self.order_confirmation_no:
                try:
                    so = frappe.get_doc("Sales Order", self.order_confirmation_no)
                    so.flags.ignore_permissions = True
                    so.cancel()

                    url = get_url_to_form("Sales Order", so.name)
                    frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=so.name)), title="Sales Order Cancelled", indicator="green")
                except:
                    pass



def create_sales_order(self):
    check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
    if check_inter_company_transaction:
        if check_inter_company_transaction == 1:
            so = make_inter_company_transaction(self, "Purchase Order", self.name)

            try:
                so.save(ignore_permissions = True)
                so.submit()
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

def make_inter_company_transaction(self, doctype, source_name, target_doc=None):
    target_doctype = "Sales Order"
    source_doc  = frappe.get_doc(doctype, source_name)

    validate_inter_company_transaction(source_doc, doctype)
    details = get_inter_company_details(source_doc, doctype)

    def set_missing_values(source, target):
        if self.amended_from:
            name = frappe.db.get_value("Sales Order", {"purchase_order": source.amended_from}, "name")
            target.amended_from = name

        target.run_method("set_missing_values")

    def update_details(source_doc, target_doc, source_parent):
        if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
            target_doc.company = details.get("company")
            target_doc.supplier = details.get("party")
            target_doc.buying_price_list = source_doc.selling_price_list
        else:
            target_doc.company = details.get("company")
            target_doc.customer = details.get("party")
            target_doc.selling_price_list = source_doc.buying_price_list
    
    def account_details(source_doc, target_doc, source_parent):
        target_company = frappe.db.get_value("Purchase Order", self.name, "supplier")
        target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
        source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
    
    doclist = get_mapped_doc(doctype, source_name,	{
        doctype: {
            "doctype": target_doctype,
            "postprocess": update_details,
            "field_map": {
                "schedule_date": "delivery_date",
                "name": "po_no",
                "transaction_date": "po_date",
                "name": "purchase_orde"
            },
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
            ],
            "postprocess": account_details,
        }

    }, target_doc, set_missing_values)

    return doclist