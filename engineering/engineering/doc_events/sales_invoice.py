# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc
from engineering.api import make_inter_company_transaction, check_counter_series
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

def change_delivery_authority(name):
	dn_status = frappe.get_value("Delivery Note", name, "status")
	
	if dn_status == 'Completed':
		frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
	else:
		frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
	
	frappe.db.commit()

def validate(self, method):
	cal_full_amount(self)

def before_save(self, method):
	update_status_updater_args(self)

def before_cancel(self, method):
	update_status_updater_args(self)

def on_submit(self, method):
	create_purchase_invoice(self)
	create_sales_invoice(self)
	update_status_updater_args(self)
	self.db_set('inter_company_invoice_reference', self.purchase_invoice_ref)

def on_cancel(self, method):
	cancel_purchase_invoice(self)
	cancel_sales_invoice(self)
	update_status_updater_args(self)


def on_trash(self, method):
	delete_sales_invoice(self)
	delete_purchase_invoice(self)


# main functions start here
def cal_full_amount(self):
	for item in self.items:
		item.full_amount = max((item.full_rate * item.full_qty), (item.rate * item.qty))

def create_purchase_invoice(self):
	""" Funtion to Create Inter Company Purchase Invoice """
	
	check_inter_company_transaction = None

	if frappe.db.exists("Company",self.customer):
		check_inter_company_transaction = frappe.get_value(
			"Company", self.customer, "allow_inter_company_transaction"
		)
	
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]

		if self.company in inter_company_list:
			
			field_map = {
				"name": "bill_no",
				"posting_date": "bill_date",
			}

			child_field_map = {
				"pr_detail": "pr_detail",
				"purchase_order_item": "po_detail",
			}

			pi = make_inter_company_transaction(
				self,
				"Sales Invoice",
				"Purchase Invoice",
				"sales_invoice_ref",
				field_map = field_map,
				child_field_map = child_field_map
			)

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
			
			if authority == "Unauthorized" and (not pi.amended_from) and self.ref_invoice:
				
				alternate_company = frappe.db.get_value("Company", pi.company, 'alternate_company')
				company_series = frappe.db.get_value("Company", alternate_company, 'company_series')

				pi.company_series = frappe.db.get_value("Company", pi.name, "company_series")
				pi.series_value = check_counter_series(pi.naming_series, company_series) - 1
				pi.naming_series = 'A' + pi.naming_series
			
			pi.sales_invoice_ref = self.name
			pi.save(ignore_permissions = True)
			pi.submit()

			if self.ref_invoice:
				
				ref_invoice = frappe.db.get_value("Sales Invoice", self.name, 'purchase_invoice_ref')
				
				frappe.db.set_value("Purchase Invoice", pi.name, 'ref_invoice', ref_invoice)
				frappe.db.set_value("Purchase Invoice", ref_invoice, 'ref_invoice', pi.name)

			self.db_set('purchase_invoice_ref', pi.name)                

def create_sales_invoice(self):
	""" Function to Create another Sales Invoice on Submit """

	authority = frappe.db.get_value("Company", self.company, "authority")
	
	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			if frappe.db.exists("Company", source.customer):
				target.customer = frappe.db.get_value("Company", source.customer, "alternate_company")
			
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
			if source.debit_to:
				target.debit_to = source.debit_to.replace(
					source_company_abbr, target_company_abbr
				)
			
			if source.taxes_and_charges:
				target.taxes_and_charges = source.taxes_and_charges.replace(
					source_company_abbr, target_company_abbr
				)

				for index, item in enumerate(source.taxes):
					target.taxes[index].charge_type = "Actual"
					target.taxes[index].included_in_print_rate = 0
					target.taxes[index].account_head = item.account_head.replace(
						source_company_abbr, target_company_abbr
					)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Sales Invoice", {"ref_invoice": source.amended_from}, "name")
			
			target.run_method('set_missing_values')
		
		def update_accounts(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

			doc = frappe.get_doc("Company", target_company)

			target_doc.income_account = doc.default_income_account
			target_doc.expense_account = doc.default_expense_account
			target_doc.cost_center = doc.cost_center
		
		fields = {
			"Sales Invoice": {
				"doctype": "Sales Invoice",
				"field_map": {
					"ref_invoice": "name",
				},
				"field_no_map":{
					"authority",
					"company_series",
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
		si.series_value = self.series_value
		
		si.save(ignore_permissions = True)
		si.submit() 

		for i in self.items:
			change_delivery_authority(i.delivery_docname)

		self.db_set('ref_invoice', si.name)


def cancel_sales_invoice(self):
	si = None
	
	if self.ref_invoice:
		si = frappe.get_doc("Sales Invoice", {'ref_invoice':self.name})
	
	if si:
		si.flags.ignore_permissions = True
		si.flags.ignore_links = True

		if si.docstatus == 1:
			si.flags.ignore_permissions = True
			si.cancel()


def cancel_purchase_invoice(self):
	pi = None

	if self.purchase_invoice_ref:
		pi = frappe.get_doc("Purchase Invoice", self.purchase_invoice_ref)

	if pi:
		pi.flags.ignore_permissions = True
		pi.flags.ignore_links = True

		if pi.docstatus == 1:
			pi.cancel()

def delete_purchase_invoice(self):
	if self.purchase_invoice_ref:
		frappe.db.set_value("Purchase Invoice", self.purchase_invoice_ref, 'sales_invoice_ref', '')    
		frappe.db.set_value("Purchase Invoice", self.purchase_invoice_ref, 'inter_company_invoice_reference', '')

		frappe.db.set_value("Sales Invoice", self.name, 'purchase_invoice_ref', '')    
		frappe.db.set_value("Sales Invoice", self.name, 'inter_company_invoice_reference', '')
		
		frappe.delete_doc("Purchase Invoice", self.purchase_invoice_ref, force = 1, ignore_permissions=True)  

def delete_sales_invoice(self):
	if self.ref_invoice:
		frappe.db.set_value("Sales Invoice", self.name, 'ref_invoice', '')    
		frappe.db.set_value("Sales Invoice", self.ref_invoice, 'ref_invoice', '') 
		
		frappe.delete_doc("Sales Invoice", self.ref_invoice, force = 1, ignore_permissions=True)

def update_status_updater_args(self):
	self.status_updater[0]['target_parent_field'] = 'full_amount'