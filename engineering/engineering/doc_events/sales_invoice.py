# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import check_counter_series, validate_inter_company_transaction, get_inter_company_details
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

def before_naming(self, method):
	naming_opening_invoice(self)

def before_validate(self, method):
	setting_amount_and_rate(self)
	update_discounted_net_total(self)

def validate(self, method):
	setting_alternate_company_as_branch(self)
	calculate_full_amount(self)

def on_submit(self, method):
	pass
	# if not self.dont_replicate:
	# 	create_purchase_invoice(self)
	# 	create_branch_company_sales_invoice(self)
	# 	create_sales_invoice(self)
	# 	self.db_set('inter_company_invoice_reference', self.pi_ref)

def on_trash(self, method):
	delete_all(self)

def on_cancel(self, method):
	cancel_all(self)

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

def naming_opening_invoice(self):
	if self.is_opening == "Yes":
		if not self.get('name'):
			self.naming_series = 'O' + self.naming_series

def setting_amount_and_rate(self):
	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0) * (item.real_qty or 0)
		item.discounted_net_amount = item.discounted_amount
	
	if self.authority != "Authorized":
		if not self.si_ref:
			for item in self.items:
				item.full_qty = item.qty
				item.full_rate = item.rate

def setting_alternate_company_as_branch(self):
	if self.authority == "Authorized":
		if not self.alternate_company:
			self.alternate_company = self.branch

def calculate_full_amount(self):
	for item in self.items:
		item.full_amount = max((item.full_rate * item.full_qty), (item.rate * item.qty))

def create_purchase_invoice(self):
	check_inter_company_transaction = None

	if frappe.db.exists("Company",self.customer):
		check_inter_company_transaction = frappe.get_value(
			"Company", self.customer, "allow_inter_company_transaction"
		)
	
	if check_inter_company_transaction:
		
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]
	
		if self.company in inter_company_list:
			pi = make_inter_company_transaction(self)

			for index, item in enumerate(self.items):
				if item.delivery_note:
					pi.items[index].purchase_receipt = frappe.db.get_value(
						"Delivery Note",
						item.delivery_note,
						'inter_company_receipt_reference'
					)

				if item.sales_order:
					pi.items[index].purchase_order = frappe.db.get_value(
						"Sales Order",
						item.sales_order,
						'inter_company_order_reference'
					)
		
			authority = frappe.db.get_value("Company", pi.company, 'authority')
				
			if authority == "Unauthorized" and (not pi.amended_from) and self.si_ref:
				
				alternate_company = self.alternate_company
				company_series = frappe.db.get_value("Company", alternate_company, 'company_series')

				pi.company_series = frappe.db.get_value("Company", pi.name, "company_series")
				pi.series_value = check_counter_series(pi.naming_series, company_series) - 1
				pi.naming_series = 'A' + pi.naming_series
			
			pi.si_ref = self.name

			pi.save()
			if self.update_stock:
				pi.db_set('update_stock', 1)
			
			pi.submit()
			
			if self.si_ref:
				si_ref = frappe.db.get_value("Sales Invoice", self.name, 'si_ref')
				pi_ref = frappe.db.get_value("Sales Invoice", self.name, 'pi_ref')
				
				frappe.db.set_value("Purchase Invoice", pi.name, 'si_ref', self.name)
				frappe.db.set_value("Purchase Invoice", pi_ref, 'si_ref', si_ref)

			self.db_set('pi_ref', pi.name)

def create_branch_company_sales_invoice(self):
	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.through_company
			target.customer = source.company

			target.set_posting_time = 1

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges

			if self.amended_from:
				target.amended_from = frappe.db.get_value("Sales Invoice", {"branch_invoice_ref": source.amended_from}, "name")
			
			if source.debit_to:
				target.debit_to = source.debit_to.replace(
					source_company_abbr, target_company_abbr
				)
			if source.items[0].delivery_note_item:
				target.selling_price_list = frappe.db.get_value("Delivery Note",
					frappe.db.get_value("Delivery Note Item", source.items[0].delivery_note_item, 'parent')
				,'selling_price_list')
			
			if source.write_off_account:
				target.write_off_account = source.write_off_account.replace(source_company_abbr, target_company_abbr)
			
			if source.write_off_cost_center:
				target.write_off_cost_center = source.write_off_cost_center.replace(source_company_abbr, target_company_abbr)
			
			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")
		
		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.through_company, "abbr")

			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)

			if source_doc.income_account:
				target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)

			if source_doc.delivery_note_item:
				target_doc.delivery_note = frappe.db.get_value("Delivery Note Item", source_doc.delivery_note_item, 'parent')
				target_doc.dn_detail = source_doc.delivery_note_item
			
			if source_doc.sales_order_item:
				target_doc.sales_order = frappe.db.get_value("Sales Order Item", source_doc.sales_order_item, 'parent')
				target_doc.so_detail = source_doc.sales_order_item
			
			if source_doc.delivery_note_item:
				target_doc.rate = frappe.db.get_value("Delivery Note Item", source_doc.delivery_note_item, 'rate')
				target_doc.discounted_rate = frappe.db.get_value("Delivery Note Item", source_doc.delivery_note_item, 'discounted_rate')


		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.through_company, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)
		
		fields = {
			"Sales Invoice": {
				"doctype": "Sales Invoice",
				"field_map": {
					"name": "branch_invoice_ref",
					"ignore_pricing_rule": "ignore_pricing_rule",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"write_off_amount": "write_off_amount",
					"base_write_off_amount": "base_write_off_amount",
					"write_off_outstanding_amount_automatically": "write_off_outstanding_amount_automatically",
				},
				"field_no_map":{
					"authority",
					"company_series",
					"update_stock",
					"authority",
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
					"final_customer",
					"si_ref",
					"inter_company_invoice_reference",
					"pi_ref",
					"branch",
					"alternate_company",
					"real_difference_amount"
				},
			},
			"Sales Invoice Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"batch_no": "batch_no",
					"serial_no": "serial_no",
				},
				"field_no_map": {
					"series",
					"pr_ref",
					"po_ref",
				},
				"postprocess": update_items,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"postprocess": update_taxes,
				"field_no_map":[
					"amount"
				]
			}
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
	
	if self.through_company and self.authority == "Unauthorized":
		si = get_sales_invoice_entry(self.name)	
		si.save(ignore_permissions = True)
		si.submit()
		self.db_set("branch_invoice_ref", si.name)

	if self.authority == "Unauthorized" and not self.si_ref:
		self.db_set('pay_amount_left', self.rounded_total)

def create_sales_invoice(self):
	authority = frappe.db.get_value("Company", self.company, "authority")
	
	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			if frappe.db.exists("Company", source.customer):
				target.customer = source.alternate_company
			
			target.company = source.alternate_company or source.branch
			target.si_ref = self.name
			target.authority = "Unauthorized"

			target.set_posting_time = 1

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.debit_to:
				target.debit_to = source.debit_to.replace(
					source_company_abbr, target_company_abbr
				)
			
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(
					source_company_abbr, target_company_abbr
				)
				if frappe.db.exists("Sales Taxes and Charges Template", taxes_and_charges):
					target.taxes_and_charges = source.taxes_and_charges

			if source.taxes:
				for index, item in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					target.taxes[index].account_head = item.account_head.replace(
						source_company_abbr, target_company_abbr
					)
			
			if source.write_off_account:
				target.write_off_account = source.write_off_account.replace(source_company_abbr, target_company_abbr)
			
			if source.write_off_cost_center:
				target.write_off_cost_center = source.write_off_cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Sales Invoice", {"si_ref": source.amended_from}, "name")
			target.ignore_pricing_rule = 1
			target.run_method('set_missing_values')
		
		def update_accounts(source_doc, target_doc, source_parent):
			target_company = source_parent.alternate_company

			doc = frappe.get_doc("Company", target_company)

			target_doc.income_account = doc.default_income_account
			target_doc.expense_account = doc.default_expense_account
			target_doc.cost_center = doc.cost_center
		
		fields = {
			"Sales Invoice": {
				"doctype": "Sales Invoice",
				"field_map": {
					"si_ref": "name",
					"is_return": "is_return",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"write_off_amount": "write_off_amount",
					"base_write_off_amount": "base_write_off_amount",
					"write_off_outstanding_amount_automatically": "write_off_outstanding_amount_automatically",
				},
				"field_no_map":{
					"authority",
					"company_series",
					"update_stock",
					"branch_invoice_ref",
					"branch",
					"alternate_company"
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
					"net_amount": "discounted_amount",
					"serial_no_ref": "serial_no",
					"batch_ref": "batch_no",
				},
				"field_no_map": {
					"series",
					"pr_ref",
					"po_ref",
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
		si.naming_series = 'A' + si.naming_series
		if si.items[0].delivery_docname:
			doc = frappe.get_doc("Delivery Note", si.items[0].delivery_docname)
			si.taxes_and_charges = doc.taxes_and_charges
			si.taxes = doc.taxes
		si.series_value = self.series_value
		si.save(ignore_permissions = True)
		si.save(ignore_permissions = True)
		si.submit()
		self.db_set('branch_invoice_ref', frappe.db.get_value("Sales Invoice", si.name, 'branch_invoice_ref'))
		self.db_set('si_ref', si.name)

def cancel_all(self):
	if self.si_ref:
		doc = frappe.get_doc("Sales Invoice", self.si_ref)
		if doc.docstatus == 1:
			doc.cancel()
	
	if self.pi_ref:
		doc = frappe.get_doc("Purchase Invoice", self.pi_ref)
		if doc.docstatus == 1:
			doc.cancel()
	
	if self.branch_invoice_ref:
		doc = frappe.get_doc("Sales Invoice", self.branch_invoice_ref)
		if doc.docstatus == 1:
			doc.cancel()

def delete_all(self):
	si_ref = [self.si_ref, self.branch_invoice_ref]
	pi_ref = [self.pi_ref]

	if self.si_ref:
		doc = frappe.get_doc("Sales Invoice", self.si_ref)

		si_ref.append(doc.si_ref)
		si_ref.append(doc.branch_invoice_ref)
		pi_ref.append(doc.pi_ref)
	
	if self.branch_invoice_ref:
		doc = frappe.get_doc("Sales Invoice", self.branch_invoice_ref)

		si_ref.append(doc.si_ref)
		si_ref.append(doc.branch_invoice_ref)
		pi_ref.append(doc.pi_ref)
	
	frappe.db.set_value("Sales Invoice", self.name, 'pi_ref', None)
	frappe.db.set_value("Sales Invoice",  self.name, 'si_ref', None)
	frappe.db.set_value("Sales Invoice",  self.name, 'inter_company_invoice_reference', None)
	
	for si in si_ref:
		if si:
			frappe.db.set_value("Sales Invoice", si, 'pi_ref', None)
			frappe.db.set_value("Sales Invoice", si, 'si_ref', None)
			frappe.db.set_value("Sales Invoice", si, 'inter_company_invoice_reference', None)
			frappe.db.set_value("Sales Invoice", si, 'branch_invoice_ref', None)
		
	for pi in pi_ref:
		if pi:
			frappe.db.set_value("Purchase Invoice", pi, 'pi_ref', None)
			frappe.db.set_value("Purchase Invoice", pi, 'si_ref', None)
			frappe.db.set_value("Purchase Invoice", pi, 'inter_company_invoice_reference', None)
	
	for si in si_ref:
		if si and si != self.name:
			if frappe.db.exists("Sales Invoice", si):
				frappe.delete_doc("Sales Invoice", si)
	
	for pi in pi_ref:
		if pi:
			if frappe.db.exists("Purchase Invoice", pi):
				frappe.delete_doc("Purchase Invoice", pi)

def make_inter_company_transaction(self, target_doc=None):
	source_doc  = frappe.get_doc("Sales Invoice", self.name)

	validate_inter_company_transaction(source_doc, "Sales Invoice")
	details = get_inter_company_details(source_doc, "Sales Invoice")

	def set_missing_values(source, target):
		if self.amended_from:
			name = frappe.db.get_value("Purchase Invoice", {'si_ref': self.amended_from}, "name")
			target.amended_from = name
		
		target.company = source.customer
		target.supplier = source.company
		target.buying_price_list = source.selling_price_list

		abbr = frappe.db.get_value("Company", target.company, 'abbr')

		target.set_warehouse = "Stores - {}".format(abbr)
		target.rejected_warehouse = "Stores - {}".format(abbr)

		if source.taxes_and_charges:
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")
			
			taxes_and_charges = source.taxes_and_charges.replace(
				source_company_abbr, target_company_abbr
			)

			if frappe.db.exists("Purchase Taxes and Charges Template", taxes_and_charges):
				target.taxes_and_charges = taxes_and_charges

			target.taxes = source.taxes
			
			for index, item in enumerate(source.taxes):
				target.taxes[index].account_head = item.account_head.replace(
					source_company_abbr, target_company_abbr
				)
			
		target.run_method("set_missing_values")
	
	def update_accounts(source_doc, target_doc, source_parent):
		target_company = source_parent.customer
		doc = frappe.get_doc("Company", target_company)

		if source_doc.pr_detail:
			target_doc.purchase_receipt = frappe.db.get_value("Purchase Receipt Item", source_doc.pr_detail, 'parent')
		if source_doc.purchase_order_item:
			target_doc.purchase_order = frappe.db.get_value("Purchase Order Item", source_doc.purchase_order_item, 'parent')

		target_doc.income_account = doc.default_income_account
		target_doc.expense_account = doc.default_expense_account
		target_doc.cost_center = doc.cost_center
	
	doclist = get_mapped_doc("Sales Invoice", self.name,	{
		"Sales Invoice": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"name": "bill_no",
				"posting_date": "bill_date",
			},
			"field_no_map": [
				"taxes_and_charges",
				"series_value",
				"update_stock",
				"real_difference_amount"
			],
		},
		"Sales Invoice Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"pr_detail": "pr_detail",
				"purchase_order_item": "po_detail",
			},
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse",
			], "postprocess": update_accounts,
		}

	}, target_doc, set_missing_values)

	return doclist
