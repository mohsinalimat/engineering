import frappe
from erpnext.accounts.party import get_party_account_currency
from frappe.utils import nowdate, getdate, flt
from erpnext.accounts.utils import get_fiscal_year

@frappe.whitelist()
def onload(self, method):
	load_dashboard_info(self)

def load_dashboard_info(self):
	def get_dashboard_info(party_type, party, loyalty_program=None):
		current_fiscal_year = get_fiscal_year(nowdate(), as_dict=True)

		doctype = "Sales Invoice" if party_type=="Customer" else "Purchase Invoice"

		companies = frappe.get_list(doctype, filters={
			'docstatus': 1,
			party_type.lower(): party
		}, distinct=1, fields=['company'], user=frappe.session.user)
				
		company_wise_info = []

		company_wise_grand_total = frappe.get_all(doctype,
			filters={
				'docstatus': 1,
				party_type.lower(): party,
				'posting_date': ('between', [current_fiscal_year.year_start_date, current_fiscal_year.year_end_date])
				},
				group_by="company",
				fields=["company", "sum(grand_total) as grand_total", "sum(base_grand_total) as base_grand_total"]
			)

		loyalty_point_details = []

		if party_type == "Customer":
			loyalty_point_details = frappe._dict(frappe.get_all("Loyalty Point Entry",
				filters={
					'customer': party,
					'expiry_date': ('>=', getdate()),
					},
					group_by="company",
					fields=["company", "sum(loyalty_points) as loyalty_points"],
					as_list =1
				))

		company_wise_billing_this_year = frappe._dict()

		for d in company_wise_grand_total:
			company_wise_billing_this_year.setdefault(
				d.company,{
					"grand_total": d.grand_total,
					"base_grand_total": d.base_grand_total
				})

		company_wise_total_unpaid = frappe._dict(frappe.db.sql("""
			select company, sum(debit_in_account_currency) - sum(credit_in_account_currency)
			from `tabGL Entry`
			where party_type = %s and party=%s
			group by company""", (party_type, party)))

		for d in companies:
			company_default_currency = frappe.db.get_value("Company", d.company, 'default_currency')
			party_account_currency = get_party_account_currency(party_type, party, d.company)

			if party_account_currency==company_default_currency:
				billing_this_year = flt(company_wise_billing_this_year.get(d.company,{}).get("base_grand_total"))
			else:
				billing_this_year = flt(company_wise_billing_this_year.get(d.company,{}).get("grand_total"))

			total_unpaid = flt(company_wise_total_unpaid.get(d.company))

			if loyalty_point_details:
				loyalty_points = loyalty_point_details.get(d.company)

			info = {}
			info["billing_this_year"] = flt(billing_this_year) if billing_this_year else 0
			info["currency"] = party_account_currency
			info["total_unpaid"] = flt(total_unpaid) if total_unpaid else 0
			info["company"] = d.company

			if party_type == "Customer" and loyalty_point_details:
				info["loyalty_points"] = loyalty_points

			if party_type == "Supplier":
				info["total_unpaid"] = -1 * info["total_unpaid"]

			company_wise_info.append(info)

		return company_wise_info

	info = get_dashboard_info(self.doctype, self.name, self.loyalty_program)
	self.set_onload('dashboard_info', info)