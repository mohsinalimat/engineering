# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import make_inter_company_transaction


def validate(self, method):
	cal_full_amount(self)

def before_save(self, method):
	update_status_updater_args(self)

def before_cancel(self, method):
	update_status_updater_args(self)

def on_submit(self, method):
	create_purchase_invoice(self)
	update_status_updater_args(self)
	self.db_set('inter_company_invoice_reference', self.sales_invoice_ref)

def on_cancel(self, method):
	cancel_purchase_invoice(self)
	update_status_updater_args(self)

def on_trash(self, method):
	delete_purchase_invoice(self)

def cal_full_amount(self):
	for item in self.items:
		item.full_amount = max((item.full_rate * item.full_qty), (item.rate * item.qty))

def create_purchase_invoice(self):
	authority = frappe.db.get_value("Company", self.company, "authority")
	
	def get_purchase_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):

			target.company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.ref_invoice = self.name
			target.authority = "Unauthorized"

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			for index, item in enumerate(source.items):
				if item.net_rate:
					if item.net_rate != item.rate:
						full_amount = item.full_qty * item.full_rate
						amount_diff = item.amount - item.net_amount
						try:
							target.items[index].rate = (full_amount - amount_diff) / item.full_qty
						except:
							pass
			if source.credit_to:
				target.credit_to = source.credit_to.replace(source_company_abbr, target_company_abbr)
			
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", taxes_and_charges):
					target.taxes_and_charges = taxes_and_charges
				else:
					target.taxes_and_charges = ''

			if source.taxes:
				for index, item in enumerate(source.taxes):
					target.taxes[index].charge_type = "Actual"
					target.taxes[index].included_in_print_rate = 0
					target.taxes[index].account_head = item.account_head.replace(
						source_company_abbr, target_company_abbr
					)

			if self.amended_from:
				target.amended_from = frappe.db.get_value(
					"Purchase Invoice", {"ref_invoice": source.amended_from}, "name"
				)
			
			target.run_method('set_missing_values')
		
		def update_accounts(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			target_doc.income_account = doc.default_income_account
			target_doc.expense_account = doc.default_expense_account
			target_doc.cost_center = doc.cost_center
			
			if source_doc.warehouse:
				target_doc.warehouse = source_doc.warehouse.replace(
					source_company_abbr, target_company_abbr
				)
			
			if source_doc.rejected_warehouse:
				target_doc.rejected_warehouse = source_doc.rejected_warehouse.replace(
					source_company_abbr, target_company_abbr
				)
		
		fields = {
			"Purchase Invoice": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"ref_invoice": "name",
				},
				"field_no_map":{
					"authority",
					"company_series",
				}
			},
			"Purchase Invoice Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"item_varient": "item_code",
					"item_code": "item_varient",
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
	
	if authority == "Authorized" and (not self.sales_invoice_ref):
		pi = get_purchase_invoice_entry(self.name)
		
		pi.naming_series = 'A' + pi.naming_series
		pi.series_value = self.series_value

		pi.save(ignore_permissions= True)

		if self.disable_rounded_total:
			pi.real_difference_amount = pi.rounded_total - self.rounded_total
		else:
			pi.real_difference_amount = pi.grand_total - self.grand_total
		
		pi.save(ignore_permissions= True)
		
		pi.submit()

		self.db_set('ref_invoice', pi.name)

def cancel_purchase_invoice(self):
	if not self.sales_invoice_ref:
		pi = None
		if self.ref_invoice:
			pi = frappe.get_doc("Purchase Invoice", {'ref_invoice':self.name})
		
		if pi:
			pi.flags.ignore_permissions = True
			if pi.docstatus == 1:
				pi.cancel()

def delete_purchase_invoice(self):
	if self.ref_invoice:
		
		frappe.db.set_value("Purchase Invoice", self.name, 'ref_invoice', '')
		frappe.db.set_value("Purchase Invoice", self.ref_invoice, 'ref_invoice', '')

		frappe.delete_doc("Purchase Invoice", self.ref_invoice, force = 1, ignore_permissions=True)

def update_status_updater_args(self):
	self.status_updater[0]['target_parent_field'] = 'full_amount'
