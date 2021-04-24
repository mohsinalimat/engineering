# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt,get_url_to_form
from frappe.model.mapper import get_mapped_doc


def before_validate(self, method):
	setting_real_qty(self)
	update_discounted_amount(self)
	reseting_thorugh_company(self)
	update_discounted_net_total(self)

def on_submit(self, method):
	create_purchase_order(self)

def on_cancel(self, method):
	cancel_sales_order(self)

def on_trash(self, method):
	delete_sales_purchase_order(self)

def reseting_thorugh_company(self):
	""" This function use to reset through copmany if through company is same as company """

	if self.through_company == self.company:
		self.through_company == None

def setting_real_qty(self):
	""" This function is use to set real qty on save """

	for item in self.items:
		if not item.real_qty:
			item.real_qty = item.qty

def update_discounted_amount(self):
	""" This function is use to update discounted amonunt and net amount in sales order item """

	for item in self.items:
		item.discounted_rate = item.discounted_rate if item.discounted_rate else 0
		item.real_qty = item.real_qty if item.real_qty else 0

		item.discounted_amount = item.discounted_rate * flt(item.real_qty)
		item.discounted_net_amount = item.discounted_amount

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	testing_only_tax = 0
	
	for tax in self.taxes:
		if tax.testing_only:
			testing_only_tax += tax.tax_amount
	
	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges - testing_only_tax
	self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total

def create_purchase_order(self):
	""" This function is use to create purchase order on submit of sales order in inter company invoice """

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
					# frappe.throw("Please define item price for item {} in price list {}".format(frappe.bold(item.item_code), frappe.bold(target.buying_price_list)))
					item.rate = 0
			
			target.set_posting_time = 1
			target.transaction_date = source.transaction_date

			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			if source_doc.get('income_account'):
				target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.get('expense_account'):
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.get('cost_center'):
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)
			
			if source_doc.get('delivery_date'):
				target_doc.schedule_date = source_doc.delivery_date
			
			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			buying_price_list = None
			company_doc = frappe.get_doc("Company", source_parent.through_company)
			for com in company_doc.allowed_to_transact_with:
				if com.company == source_parent.company:
					buying_price_list = com.price_list
			if not buying_price_list:
				frappe.throw(f"Set Buying price list for company in inter company {source_parent.through_company}.")
			
			if frappe.db.exists("Item Price", {'item_code': source_doc.item_code, 'price_list': buying_price_list}):
				target_doc.rate = frappe.db.get_value("Item Price", {'item_code': source_doc.item_code, 'price_list': buying_price_list}, 'price_list_rate')
			else:
				# frappe.throw("Please define item price for item {} in price list {}".format(frappe.bold(source_doc.item_code), frappe.bold(buying_price_list)))
				target_doc.rate = 0
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
					"schedule_date": "delivery_date",
					"po_date": "transaction_date",
					"shipping_address_name": "shipping_address",
					"customer_gstin": "company_gstin",
					"shipping_address": "shipping_address_display",
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
					"customer_name",
					"through_company",
					"customer_gstin",
					"contact_person",
					"address_display",
					"billing_gstin",
					"customer_address",
					"company_address_display",
					"company_address",
					"through_company",
					"set_warehouse"
				]
			},
			"Sales Order Item": {
				"doctype": "Purchase Order Item",
				"field_map": {
					"purchase_order_item": "purchase_order_item",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"name": "sales_order_item",
					"schedule_date": "delivery_date",
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
		doc.flags.ignore_permissions = True
		if doc.docstatus == 1:
			doc.cancel()
	
	if self.po_ref:
		po = frappe.get_doc("Purchase Order", self.po_ref)
		po.flags.ignore_permissions = True
		if po.docstatus == 1:
			po.cancel()

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

def get_price_list(self):
	company_doc = frappe.get_doc("Company", self.company)
	for com in company_doc.allowed_to_transact_with:
		if com.company == self.customer:
			if com.price_list:
				self.selling_price_list = com.price_list
			else:
				frappe.throw("Add price list in Company {0} for customer {1}".format(self.company,self.customer))

@frappe.whitelist()
def get_last_5_transaction_details(name, item_code, customer):
	data = frappe.db.sql("""
		SELECT soi.qty, soi.rate, so.transaction_date, so.company,so.name 
		FROM `tabSales Order Item` as soi JOIN `tabSales Order` as so on soi.parent=so.name 
		WHERE soi.name != '{}' and so.customer = '{}' and soi.item_code = '{}' and so.docstatus = 1
		ORDER By so.transaction_date DESC LIMIT 5	
	""".format(name, customer, item_code), as_dict = 1)

	table = """<table class="table table-bordered" style="margin: 0; font-size:80%;">
		<thead>
			<tr>
				<th>Sales Order</th>
				<th>Company</th>
				<th>Date</th>
				<th>Qty</th>
				<th>Rate</th>

			<tr>
		</thead>
	<tbody>"""
	for i in data:
		table += f"""
			<tr>
				<td>{"<a href='{0}' target='_blank'>{1}</a>".format(get_url_to_form("Sales Order",i.name),i.name)}</td>
				<td>{i.company}</td>
				<td>{frappe.format(i.transaction_date, {'fieldtype': 'Date'})}</td>
				<td>{i.qty}</td>
				<td>{i.rate}</td>
			</tr>
		"""
	
	table += """
	</tbody></table>
	"""
	return table