import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


def validate(self, method):
	"""On Submit Custom Function for Sales Invoice"""
	account(self)

def account(self):
	if self.company:

		# Getting authority of company
		authority = frappe.db.get_value("Company", self.company, "authority")

		if authority == "Authorized":
			target_company = frappe.db.get_value("Company", self.company, "alternate_company")
			
			if frappe.db.exists("Account", {"company": target_company, "account_name": self.account_name}):
				a = frappe.get_doc("Account", {"company": target_company, "account_name": self.account_name})
			else:
				a = frappe.new_doc("Account")
				a.account_name = self.account_name
				a.company = frappe.db.get_value("Company", self.company, "alternate_company")
			
			a.freeze_account = self.freeze_account
			a.account_currency = self.account_currency
			a.account_type = self.account_type

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

			if self.parent_account:
				a.parent_account = self.parent_account.replace(source_company_abbr, target_company_abbr)
			
			a.is_group = self.is_group
			a.balance_must_be = self.balance_must_be
			a.report_type = self.report_type
			a.root_type = self.root_type
			
			if self.disabled:
				a.disabled = s.disabled

			try:
				a.save(ignore_permissions = True)
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)