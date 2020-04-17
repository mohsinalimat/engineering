# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz Tech Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import get_url_to_form
from frappe.model.mapper import get_mapped_doc

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
	def get_sales_order_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.supplier
			target.customer = source.company

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges

			if self.amended_from:
				name = frappe.db.get_value(target_doctype, {link_field: self.amended_from}, "name")
				target.amended_from = name

			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.supplier, "abbr")

			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)

		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.supplier, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)
			
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Purchase Order": {
				"doctype": "Sales Order",
				"field_map": {
					"schedule_date": "delivery_date",
					"name": "po_no",
					"name": "po_ref",
					"transaction_date": "po_date",
					"selling_price_list": "buying_price_list",
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
				]
			},
			"Purchase Order Item": {
				"doctype": "Sales Order Item",
				"field_map": {
					"name": "purchase_order_item",
				},
				"field_no_map": [
					"warehouse",
					"cost_center",
					"expense_account",
					"income_account",
				],
				"postprocess": update_items,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"postprocess": update_taxes,
			}
		}

		doc = get_mapped_doc(
			"Purchase Order",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doc

	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.company)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]
		
		if self.supplier in inter_company_list:
			so = get_sales_order_entry(self.name)
			
			so.save(ignore_permissions = True)
			so.submit()

			self.db_set('order_confirmation_no', so.name)
			self.db_set('order_confirmation_date', so.transaction_date)
			self.db_set('inter_company_order_reference', so.name)
			self.db_set('so_ref', so.name)

			so.db_set('inter_company_order_reference', self.name)

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
