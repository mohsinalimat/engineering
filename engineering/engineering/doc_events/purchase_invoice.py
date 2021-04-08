# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import make_inter_company_transaction


def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0.0) * (item.real_qty or 0.0)
		item.discounted_net_amount = item.discounted_amount
	
	if self.amended_from and self.authority == "Unauthorized" and not self.pi_ref:
		if frappe.db.exists("Purchase Invoice", {"pi_ref": self.amended_from}):
			frappe.throw("You Can not save this Invoice!")

	if not self.alternate_company and self.branch and self.authority == "Authorized":
		self.alternate_company = self.branch

def before_naming(self, method):
	if self.is_opening == "Yes":
		if not self.get('name'):
			self.naming_series = 'O' + self.naming_series

def validate(self, method):
	cal_full_amount(self)

def before_save(self, method):
	pass

def before_cancel(self, method):
	pass

def on_submit(self, method):
	# change_purchase_receipt_rate(self)
	create_purchase_invoice(self)
	self.db_set('inter_company_invoice_reference', self.si_ref)

def on_cancel(self, method):
	cancel_purchase_invoice(self)

def on_trash(self, method):
	delete_purchase_invoice(self)

def cal_full_amount(self):
	for item in self.items:
		item.full_amount = max((item.full_rate * item.full_qty), (item.rate * item.qty))

def create_purchase_invoice(self):
	authority = frappe.db.get_value("Company", self.company, "authority")
	
	def get_purchase_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):

			target.company = self.alternate_company or self.branch
			target.pi_ref = self.name
			target.authority = "Unauthorized"

			target.set_posting_time = 1

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.credit_to:
				target.credit_to = source.credit_to.replace(source_company_abbr, target_company_abbr)
			
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Purchase Taxes and Charges", taxes_and_charges):
					target.taxes_and_charges = taxes_and_charges

			if source.taxes:
				for index, item in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					target.taxes[index].account_head = item.account_head.replace(
						source_company_abbr, target_company_abbr
					)

			if self.amended_from:
				target.amended_from = frappe.db.get_value(
					"Purchase Invoice", {"pi_ref": source.amended_from}, "name"
				)

			if source.write_off_account:
				target.write_off_account = source.write_off_account.replace(source_company_abbr, target_company_abbr)
			
			if source.write_off_cost_center:
				target.write_off_cost_center = source.write_off_cost_center.replace(source_company_abbr, target_company_abbr)
			
			target.run_method('set_missing_values')
			target.run_method('calculate_taxes_and_totals')
		
		def update_accounts(source_doc, target_doc, source_parent):
			target_company = self.alternate_company or self.branch
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)
			
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
					"pi_ref": "name",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"write_off_amount": "write_off_amount",
					"base_write_off_amount": "base_write_off_amount",
				},
				"field_no_map":{
					"authority",
					"company_series",
					"update_stock"
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
					"net_amount": "discounted_amount",
				},
				"field_no_map": {
					"full_rate",
					"full_qty",
					"series",
					"net_rate"
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
	
	if authority == "Authorized" and (not self.si_ref):
		pi = get_purchase_invoice_entry(self.name)
		
		pi.naming_series = 'A' + pi.naming_series
		pi.series_value = self.series_value
		if pi.items[0].purchase_receipt_docname:
			doc = frappe.get_doc("Purchase Receipt", pi.items[0].purchase_receipt_docname)
			pi.taxes_and_charges = doc.taxes_and_charges
			pi.taxes = doc.taxes

		pi.save(ignore_permissions= True)

		if self.disable_rounded_total:
			pi.real_difference_amount = pi.rounded_total - self.rounded_total
		else:
			pi.real_difference_amount = pi.grand_total - self.grand_total
		
		pi.save(ignore_permissions= True)
		pi.submit()
		
		self.db_set('pi_ref', pi.name)

def cancel_purchase_invoice(self):
	if not self.si_ref:
		pi = None
		if self.pi_ref and not self.is_return:
			pi = frappe.get_doc("Purchase Invoice", {'pi_ref':self.name})
		
		if pi:
			pi.flags.ignore_permissions = True
			if pi.docstatus == 1:
				pi.cancel()

def delete_purchase_invoice(self):
	if self.pi_ref and not self.is_return:
		
		frappe.db.set_value("Purchase Invoice", self.name, 'pi_ref', '')
		frappe.db.set_value("Purchase Invoice", self.pi_ref, 'pi_ref', '')

		frappe.delete_doc("Purchase Invoice", self.pi_ref, force = 1, ignore_permissions=True)

def change_purchase_receipt_rate(self):
	change_item_details = {}
	for item in self.items:
		if item.purchase_receipt and item.pr_detail:
			pr_item_doc = frappe.get_doc("Purchase Receipt Item",item.pr_detail)
			if item.item_code == pr_item_doc.item_code and item.rate != pr_item_doc.rate:
				change_item_details.setdefault(pr_item_doc.item_code + pr_item_doc.name,item.rate)

	if change_item_details:
		pr_doc = frappe.get_doc("Purchase Receipt",self.items[0].purchase_receipt)
		pr_doc.db_set('docstatus',0)

		for item in pr_doc.items:
			if change_item_details.get(item.item_code + item.name) and not item.serial_no:
				item.rate = change_item_details.get(item.item_code + item.name)
		pr_doc.save(ignore_permissions = True)
		pr_doc.db_set('docstatus',1)

		frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no='{}'".format(pr_doc.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no='{}'".format(pr_doc.name))

		pr_doc.update_stock_ledger()
		pr_doc.make_gl_entries()
