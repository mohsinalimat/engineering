# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz Tech Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import get_url_to_form
from engineering.api import make_inter_company_transaction

def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = item.discounted_rate * item.real_qty
		item.discounted_net_amount = item.discounted_amount

def on_submit(self, method):
	create_sales_order(self)
	alternate_company = frappe.db.get_value("Company", self.company, "alternate_company")
	for row in self.items:
		if row.real_qty == 0:
			frappe.msgprint("Row: {} The real quantity for item {} is 0, you can not make reciept in company {} for this item".format(row.idx, row.item_name, alternate_company))

def on_cancel(self, method):
	cancel_sales_order(self)

def on_trash(self, method):
	delete_sales_order(self)

def create_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")

	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.company)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]
		
		if self.supplier in inter_company_list:
			field_map = {
				"schedule_date": "delivery_date",
				"name": "po_no",
				"transaction_date": "po_date",
			}
			child_field_map = {
				"name": "purchase_order_item",
			}
			so = make_inter_company_transaction(self, "Purchase Order", "Sales Order", "ref_po", field_map = field_map, child_field_map = child_field_map)
			so.save(ignore_permissions = True)
			so.submit()
			
			frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_no', so.name)
			frappe.db.set_value('Purchase Order', self.name, 'inter_company_order_reference', so.name)
			frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_date', so.transaction_date)

			frappe.db.set_value("Sales Order", so.name, 'inter_company_order_reference', self.name)
			frappe.db.set_value("Sales Order", so.name, 'purchase_order', self.name)

			url = get_url_to_form("Sales Order", so.name)
			frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=so.name)), title="Sales Order Created", indicator="green")
			
			frappe.db.set_value('Purchase Order', self.name, 'ref_so', so.name)

			frappe.db.set_value("Sales Order", so.name, 'inter_company_order_reference', self.name)
			frappe.db.set_value("Sales Order", so.name, 'ref_po', self.name)

			url = get_url_to_form("Sales Order", so.name)
			frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=so.name)), title="Sales Order Created", indicator="green")


def cancel_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
	if check_inter_company_transaction:
		if check_inter_company_transaction == 1:
			company = frappe.get_doc("Company", self.company)
			inter_company_list = [item.company for item in company.allowed_to_transact_with]
			if self.supplier in inter_company_list:
				if self.ref_so:
					so = frappe.get_doc("Sales Order", self.ref_so)
					so.flags.ignore_permissions = True
					so.cancel()

					url = get_url_to_form("Sales Order", so.name)
					frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=so.name)), title="Sales Order Cancelled", indicator="red")

def delete_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		if check_inter_company_transaction == 1:
			company = frappe.get_doc("Company", self.company)
			inter_company_list = [item.company for item in company.allowed_to_transact_with]
			
			if self.supplier in inter_company_list:
				frappe.db.set_value("Purchase Order", self.name, 'inter_company_order_reference', '')
				frappe.db.set_value("Purchase Order", self.name, 'ref_so', '')
				frappe.db.set_value("Purchase Order", self.name, 'order_confirmation_no', '')

				frappe.db.set_value("Sales Order", self.ref_so, 'inter_company_order_reference', '')
				frappe.db.set_value("Sales Order", self.ref_so, 'ref_po', '')
				frappe.db.set_value("Sales Order", self.ref_so, 'po_no', '')
				
				frappe.delete_doc("Sales Order", self.ref_so, force = 1, ignore_permissions=True)
				frappe.msgprint(_("Sales Order <b>{name}</b> has been deleted!".format(name=self.ref_so)), title="Sales Order Deleted", indicator="red")
