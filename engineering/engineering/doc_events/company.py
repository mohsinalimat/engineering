from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


def on_update(self, method):
	create_internal_customer_supplier(self,method)

def create_internal_customer_supplier(self,method):
	if self.allow_inter_company_transaction:
		if frappe.db.exists("Customer", {"represents_company": self.name}):
			customer = frappe.get_doc("Customer",self.name)
			customer.companies = []
			companies =  [d.company for d in frappe.get_all('Allowed To Transact With', filters = {'parent': customer.name}, fields=['company'])]
			for raw in self.allowed_to_transact_with:
				customer.append("companies",{
					'company':raw.company
				})
			customer.save(ignore_permissions=True)
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = self.name
			customer.customer_group = "Internal"
			customer.is_internal_customer = 1
			customer.customer_type = "Company"
			customer.gst_category = "Registered Regular"
			customer.represents_company = self.name
			customer.tax_id = self.tax_id
			# customer.inter_company_price_list= self.default_price_list
			customer.default_currency = self.default_currency
			for raw in self.allowed_to_transact_with:
				customer.append("companies",{
					'company':raw.company
				})
			customer.save(ignore_permissions=True)
			frappe.msgprint(_("Created customer repesenting this company"))
		if frappe.db.exists("Supplier", {"represents_company": self.name}):
			supplier = frappe.get_doc("Supplier",self.name)
			companies =  [d.company for d in frappe.get_all('Allowed To Transact With', filters = {'parent': supplier.name}, fields=['company'])]
			supplier.companies = []
			for raw in self.allowed_to_transact_with:
				supplier.append("companies",{
					'company':raw.company
				})
			supplier.save(ignore_permissions=True)
		else:
			supplier = frappe.new_doc("Supplier")
			supplier.supplier_name = self.name
			supplier.supplier_group = "Internal"
			supplier.is_internal_supplier = 1
			supplier.supplier_type = "Company"
			supplier.gst_category = "Registered Regular"
			supplier.represents_company = self.name
			# customer.inter_company_price_list= self.default_price_listt
			supplier.tax_id = self.tax_id
			supplier.default_currency = self.default_currency
			for raw in self.allowed_to_transact_with:
				supplier.append("companies",{
					'company':raw.company
				})
			supplier.save(ignore_permissions=True)
			frappe.msgprint(_("Created supplier repesenting this company"))

