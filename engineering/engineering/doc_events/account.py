# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.mapper import get_mapped_doc


def validate(self, method):
	""" Custom Validate Function """
	
	update_account(self)

def update_account(self):
	""" Function to create or update account in alternate company """

	if self.company:
		# getting authority of company
		authority = frappe.db.get_value("Company", self.company, "authority")

		# if company is authorized than only create copy or update Accounts of alternate company
		if authority == "Authorized":

			# getting name of alternate company in target_company
			target_company = frappe.db.get_value("Company", self.company, "alternate_company")

			# getting abbreviation of current and target company
			source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")

			# if accounts exists in alternate company then update that account or create new account
			if frappe.db.exists("Account", {"company": target_company, "account_name": self.account_name}):
				a = frappe.get_doc("Account", {"company": target_company, "account_name": self.account_name})
			else:
				a = frappe.new_doc("Account")
				a.account_name = self.account_name
				a.company = frappe.db.get_value("Company", self.company, "alternate_company")

			if self.parent_account:
				a.parent_account = self.parent_account.replace(source_company_abbr, target_company_abbr)

			a.account_currency = self.account_currency
			a.account_type = self.account_type
			a.freeze_account = self.freeze_account
			a.is_group = self.is_group
			a.balance_must_be = self.balance_must_be
			a.report_type = self.report_type
			a.root_type = self.root_type
			a.disabled = self.disabled

			try:
				a.save()
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
