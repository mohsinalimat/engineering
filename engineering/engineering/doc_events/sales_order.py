# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc

from engineering.api import update_discounted_amount	

def before_validate(self, method):
	update_discounted_amount(self)
	if self.through_company == self.company:
		self.through_company == None

def on_submit(self, method):
	# create_sales_order(self)
	create_purchase_order(self)

def on_cancel(self, method):
	cancel_sales_order(self)

def on_trash(self, method):
	delete_sales_purchase_order(self)

def delete_sales_purchase_order(self):
	so_ref = [self.so_ref, self.name]
	po_ref = [
		self.po_ref,
		frappe.db.get_value("Sales Order", self.so_ref, 'po_ref')
	]

	for so in so_ref:
		if so:
			frappe.db.set_value("Sales Order", so, 'po_ref', '')
			frappe.db.set_value("Sales Order", so, 'so_ref', '')
			frappe.db.set_value("Sales Order", so, 'inter_company_order_reference', '')
	
	for po in po_ref:
		if po:
			frappe.db.set_value("Purchase Order", po, 'so_ref', '')
			frappe.db.set_value("Purchase Order", po, 'inter_company_order_reference', '')
	
	for so in so_ref:
		if so and so != self.name:
			if frappe.db.exists("Sales Order", so):
				frappe.delete_doc("Sales Order", so)
	
	for po in po_ref:
		if po:
			if frappe.db.exists("Purchase Order", po):
				frappe.delete_doc("Purchase Order", po)

	if self.so_ref:
		frappe.db.set_value("Sales Order", self.so_ref, 'so_ref', None)

		if frappe.db.exists("Sales Order", self.so_ref):
			frappe.delete_doc("Sales Order", self.so_ref)
	
	if self.po_ref:
		frappe.db.set_value("Purchase Order", self.po_ref, "so_ref", None)
		frappe.db.set_value("Purchase Order", self.po_ref, "inter_company_order_reference", None)

		frappe.db.set_value("Sales Order", self.name, "po_ref", None)
		frappe.db.set_value("Sales Order", self.name, "inter_company_order_reference", None)

		if frappe.db.exists("Purchase Order", self.po_ref):
			frappe.delete_doc("Purchase Order", self.po_ref)

def create_sales_order(self):
	def get_sales_order_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.through_company
			target.customer = source.company

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges

			if self.amended_from:
				target.amended_from = frappe.db.get_value("Sales Order", {'so_ref': self.amended_from}, "name")

			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.through_company, "abbr")

			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)

		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.through_company, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Sales Order": {
				"doctype": "Sales Order",
				"field_map": {
					"name": "supplier_delivery_note",
					"selling_price_list": "buying_price_list",
					"name": "so_ref"
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
					"customer_name",
					"through_company"
				]
			},
			"Sales Order Item": {
				"doctype": "Sales Order Item",
				"field_map": {
					"purchase_order_item": "purchase_order_item",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"name": "sales_order_item",
					"delivery_date": "delivery_date",
				},
				"field_no_map": [
					"warehouse",
					"cost_center",
					"expense_account",
					"income_account",
					"real_qty",
					"discounted_rate",
					"through_company"
				],
				"postprocess": update_items,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"postprocess": update_taxes,
			}
		}

		doc = get_mapped_doc(
			"Sales Order",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doc
		
	if self.through_company:
		se = get_sales_order_entry(self.name)
		se.save(ignore_permissions = True)
		se.submit()

		self.db_set("so_ref", se.name)
		for idx, item in enumerate(self.items):
			item.db_set('sales_order_item', se.items[idx].name)

def create_purchase_order(self):
	def get_purchase_order_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.company
			target.supplier = source.through_company

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Purchase Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges

			if self.amended_from:
				so_ref = frappe.db.get_value("Sales Order", source.amended_from, 'so_ref')
				target.amended_from = frappe.db.get_value("Purchase Order", {'so_ref': so_ref}, "name")
				# frappe.throw(str(target.amended_from))
			
			company_doc = frappe.get_doc("Company", target.supplier)

			for com in company_doc.allowed_to_transact_with:
				if com.company == target.company:
					if com.price_list:
						target.buying_price_list = com.price_list
					else:
						frappe.throw("Add price list for company {}".format(target.company))
			
			for item in source.items:
				if frappe.db.exists("Item Price", {'item_code': item.item_code, 'price_list': target.buying_price_list}):
					item.rate = frappe.db.get_value("Item Price", {'item_code': item.item_code, 'price_list': target.buying_price_list}, 'price_list_rate')
				else:
					frappe.throw("Please define item price for item {} in price list {}".format(frappe.bold(item.item_code), frappe.bold(target.buying_price_list)))
			
			# frappe.throw("Hello")

			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			buying_price_list = None
			company_doc = frappe.get_doc("Company", source_parent.through_company)
			for com in company_doc.allowed_to_transact_with:
				if com.company == source_parent.company:
					buying_price_list = com.price_list
			
			if frappe.db.exists("Item Price", {'item_code': source_doc.item_code, 'price_list': buying_price_list}):
				target_doc.rate = frappe.db.get_value("Item Price", {'item_code': source_doc.item_code, 'price_list': buying_price_list}, 'price_list_rate')
			else:
				frappe.throw("Please define item price for item {} in price list {}".format(frappe.bold(item.item_code), frappe.bold(target.buying_price_list)))

		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Sales Order": {
				"doctype": "Purchase Order",
				"field_map": {
					"delivery_date": "schedule_date",
					"po_date": "transaction_date",
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
					"customer_name",
					"through_company",
					"shipping_address",
					"shipping_address_name",
					"customer_gstin",
					"contact_person",
					"address_display",
					"billing_gstin",
					"customer_address",
					"company_address_display",
					"company_address",
					"through_company"
				]
			},
			"Sales Order Item": {
				"doctype": "Purchase Order Item",
				"field_map": {
					"purchase_order_item": "purchase_order_item",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"name": "sales_order_item",
					"delivery_date": "delivery_date",
				},
				"field_no_map": [
					"warehouse",
					"cost_center",
					"expense_account",
					"income_account",
					"rate",
					"discounted_rate"
				],
				"postprocess": update_items,
			},
			"Sales Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"postprocess": update_taxes,
			}
		}

		doc = get_mapped_doc(
			"Sales Order",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doc
		
	if self.through_company == self.company:
		self.db_set('through_company', None)
	
	if self.through_company:
		po = get_purchase_order_entry(self.name)
		po.save(ignore_permissions = True)
		po.submit()
		self.db_set("so_ref", po.so_ref)
		frappe.db.set_value("Sales Order", po.so_ref, "so_ref", self.name)
		frappe.db.set_value("Sales Order", po.so_ref, "final_customer", self.customer)

		if po.so_ref:
			so = frappe.get_doc("Sales Order", po.so_ref)

			for idx, item in enumerate(self.items):
				item.db_set('sales_order_item', so.items[idx].name)
			
			for idx, item in enumerate(so.items):
				item.db_set('sales_order_item', self.items[idx].name)

def cancel_sales_order(self):
	if self.so_ref:
		doc = frappe.get_doc("Sales Order", self.so_ref)
		# doc.flags.ignore_permissions = True
		if doc.docstatus == 1:
			doc.cancel()
	
	if self.po_ref:
		po = frappe.get_doc("Purchase Order", self.po_ref)
		# po.flags.ignore_permissions = True
		if po.docstatus == 1:
			po.cancel()