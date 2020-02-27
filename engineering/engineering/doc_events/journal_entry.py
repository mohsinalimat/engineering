import frappe
from frappe import _

from frappe.model.mapper import get_mapped_doc

def on_submit(self, method):
	create_journal_entry(self)

def on_cancel(self, method):
	cancel_journal_entry(self)

def on_trash(self, method):
	delete_journal_entry(self)

def delete_journal_entry(self):
	if self.ref_jv:
		frappe.db.set_value("Journal Entry", self.name, 'ref_jv', '')
		frappe.db.set_value("Journal Entry", self.ref_jv, 'ref_jv', '')

		frappe.delete_doc("Purchase Invoice", self.ref_jv, force = 1, ignore_permissions=True)

def cancel_journal_entry(self):
	pi = None
	if self.ref_jv:
		pi = frappe.get_doc("Journal Entry", {'ref_jv':self.name})
	
	if pi:
		pi.flags.ignore_permissions = True
		if pi.docstatus == 1:
			pi.cancel()

def create_journal_entry(self):
	def get_journal_entry(source_name, target_doc=None, ignore_permissions= True):
		"""Function to get payment entry"""
		
		def set_missing_values(source, target):
			""""""
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

		
		def update_account(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			
			target_doc.account = source_doc.account.replace(source_company_abbr, target_company_abbr)
			target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)


		fields = {
			"Journal Entry": {
				"doctype": "Journal Entry",
				"field_map": {
					'posting_date': 'posting_date'
				},
				"field_no_map": [],
			},
			"Journal Entry Account": {
				"doctype": "Journal Entry Account",
				"field_map": {},
				"field_no_map": [
					'reference_type',
					'reference_name',
					'project',
					'is_advance',
					'user_remark'
				],
				"postprocess": update_account,
			}
		}

		doclist = get_mapped_doc(
			"Journal Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	# getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	if authority == "Authorized":
		jv = get_journal_entry(self.name)
		try:
			jv.naming_series = 'A' + jv.naming_series
			jv.series_value = self.series_value
			jv.save(ignore_permissions= True)
			self.db_set('ref_jv', jv.name)
			jv.save(ignore_permissions= True)
			jv.submit()
		except Exception as e:
			frappe.db.rollback()
			frappe.throw(e)