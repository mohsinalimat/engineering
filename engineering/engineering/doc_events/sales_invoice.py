# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import check_counter_series, validate_inter_company_transaction, get_inter_company_details
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

def before_validate(self, method):
	for item in self.items:
		if item.discounted_rate and item.real_qty:
			item.discounted_amount = item.discounted_rate * item.real_qty
			item.discounted_net_amount = item.discounted_amount
	if self.authority != "Authorized":
		if not self.si_ref:
			for item in self.items:
				item.full_qty = item.qty
				item.full_rate = item.rate

def validate(self, method):
	cal_full_amount(self)

def before_save(self, method):
	update_status_updater_args(self)

def before_cancel(self, method):
	update_status_updater_args(self)

def on_submit(self, method):
	create_purchase_invoice(self)
	create_branch_company_sales_invoice(self)
	create_sales_invoice(self)
	update_status_updater_args(self)
	self.db_set('inter_company_invoice_reference', self.pi_ref)

def on_cancel(self, method):
	# cancel_purchase_invoice(self)
	# cancel_sales_invoice(self)
	# update_status_updater_args(self)
	cancel_all(self)

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

def on_trash(self, method):
	# delete_sales_invoice(self)
	# delete_purchase_invoice(self)
	delete_all(self)

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

# main functions start here
def cal_full_amount(self):
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
			else:
				pi.submit()
			
			if self.si_ref:
				si_ref = frappe.db.get_value("Sales Invoice", self.name, 'si_ref')
				pi_ref = frappe.db.get_value("Sales Invoice", self.name, 'pi_ref')
				
				frappe.db.set_value("Purchase Invoice", pi.name, 'si_ref', self.name)
				frappe.db.set_value("Purchase Invoice", pi_ref, 'si_ref', si_ref)

			self.db_set('pi_ref', pi.name)

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
			
			target.taxes_and_charges = source.taxes_and_charges.replace(
				source_company_abbr, target_company_abbr
			)

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
				"update_stock"
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

def create_branch_company_sales_invoice(self):
	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
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
				target.amended_from = frappe.db.get_value("Sales Invoice", {"branch_invoice_ref": source.amended_from}, "name")
			
			if source.debit_to:
				target.debit_to = source.debit_to.replace(
					source_company_abbr, target_company_abbr
				)

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
					"name": "branch_invoice_ref"
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
					"alternate_company"
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
		
		# si.naming_series = 'A' + self.naming_series
		# si.name = 'A' + self.name
		# si.series_value = self.series_value
		si.save(ignore_permissions = True)

		si.real_difference_amount = si.rounded_total - self.rounded_total
		
		si.save(ignore_permissions = True)
		si.submit()
		self.db_set("branch_invoice_ref", si.name)
		# for i in self.items:
		# 	change_delivery_authority(i.delivery_docname)

		# self.db_set('si_ref', si.name)

def create_sales_invoice(self):
	authority = frappe.db.get_value("Company", self.company, "authority")
	
	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			if frappe.db.exists("Company", source.customer):
				target.customer = source.alternate_company
			
			target.company = source.alternate_company
			target.si_ref = self.name
			target.authority = "Unauthorized"

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.debit_to:
				target.debit_to = source.debit_to.replace(
					source_company_abbr, target_company_abbr
				)
			
			if source.taxes_and_charges:
				target.taxes_and_charges = source.taxes_and_charges.replace(
					source_company_abbr, target_company_abbr
				)

				for index, item in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					target.taxes[index].account_head = item.account_head.replace(
						source_company_abbr, target_company_abbr
					)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Sales Invoice", {"si_ref": source.amended_from}, "name")
			
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
		
		si.naming_series = 'A' + self.naming_series
		# si.name = 'A' + self.name
		si.series_value = self.series_value
		si.save(ignore_permissions = True)

		si.real_difference_amount = si.rounded_total - self.rounded_total
		
		si.save(ignore_permissions = True)
		si.submit()

		# for i in self.items:
		# 	change_delivery_authority(i.delivery_docname)

		self.db_set('branch_invoice_ref', frappe.db.get_value("Sales Invoice", si.name, 'branch_invoice_ref'))
		self.db_set('si_ref', si.name)

def update_status_updater_args(self):
	pass
	# self.status_updater[0]['target_parent_field'] = 'full_amount'

@frappe.whitelist()
def submit_purchase_invoice(pi_number):
	pi = frappe.get_doc("Purchase Invoice", pi_number)
	pi.flags.ignore_permissions = True
	pi.submit()
	frappe.db.commit()

def cancel_sales_invoice(self):
	si = None
	
	if self.si_ref:
		si = frappe.get_doc("Sales Invoice", {'si_ref':self.name})
	
	if si:
		si.flags.ignore_permissions = True
		si.flags.ignore_links = True

		if si.docstatus == 1:
			si.flags.ignore_permissions = True
			si.cancel()


def cancel_purchase_invoice(self):
	pi = None

	if self.pi_ref:
		pi = frappe.get_doc("Purchase Invoice", self.pi_ref)

	if pi:
		pi.flags.ignore_permissions = True
		pi.flags.ignore_links = True

		if pi.docstatus == 1:
			pi.cancel()

def delete_purchase_invoice(self):
	if self.pi_ref:
		frappe.db.set_value("Purchase Invoice", self.pi_ref, 'si_ref', '')    
		frappe.db.set_value("Purchase Invoice", self.pi_ref, 'inter_company_invoice_reference', '')

		frappe.db.set_value("Sales Invoice", self.name, 'pi_ref', '')    
		frappe.db.set_value("Sales Invoice", self.name, 'inter_company_invoice_reference', '')
		
		frappe.delete_doc("Purchase Invoice", self.pi_ref, force = 1, ignore_permissions=True)  

def delete_sales_invoice(self):
	if self.si_ref:
		frappe.db.set_value("Sales Invoice", self.name, 'si_ref', '')    
		frappe.db.set_value("Sales Invoice", self.si_ref, 'si_ref', '') 
		
		frappe.delete_doc("Sales Invoice", self.si_ref, force = 1, ignore_permissions=True)

def update_status_updater_args(self):
	# self.status_updater[0]['target_parent_field'] = 'full_amount'
	pass