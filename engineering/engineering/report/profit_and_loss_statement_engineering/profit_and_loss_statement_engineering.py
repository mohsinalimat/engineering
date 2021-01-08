# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, cint, getdate
from erpnext.accounts.utils import get_fiscal_year
from engineering.engineering.override.financial_statements_engineering import (get_period_list, get_columns,get_data, get_fiscal_year_data)

def execute(filters=None):
	period_list = get_period_list(filters.from_fiscal_year, filters.to_fiscal_year,
		filters.periodicity, filters.accumulated_values, filters.company)

	income = get_data(filters.company, "Income", "Credit", period_list, filters = filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

	expense = get_data(filters.company, "Expense", "Debit", period_list, filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True, ignore_accumulated_values_for_fy= True)

	net_profit_loss = get_net_profit_loss(income, expense, period_list, filters.company, filters.presentation_currency)

	data = []
	data.extend(income or [])
	data.extend(expense or [])

	# Finbyz Changes START: To open Dynamic and daybook engineering report
	fiscal_year = get_fiscal_year_data(filters.from_fiscal_year, filters.to_fiscal_year)
	year_start_date = getdate(fiscal_year.year_start_date)
	year_end_date = getdate(fiscal_year.year_end_date)

	for row in data:
		try:
			account_show_report = row['show_report']
		except KeyError:
			account_show_report = None

		if account_show_report:
			url = frappe.utils.get_url()
			url += f"/desk#query-report/{account_show_report}/?company={filters.get('company')}"
			row['view_report'] = f"""<a href='{url}' target="_blank" style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'>View {account_show_report}</a>"""
			# row['view_report'] = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
			# 	target="_blank" company='{filters.get('company')}' account_show_report='{account_show_report}'
			# 	onClick=open_report(this.getAttribute('company'),this.getAttribute('account_show_report'))>View {account_show_report}</button>"""
		else:
			try:
				account_name = row['account']
			except KeyError: 
				account_name = None
			if account_name:
				url = frappe.utils.get_url()
				url += f"/desk#query-report/Daybook Engineering/?company={filters.get('company')}&from_date={year_start_date}&to_date={year_end_date}&account={account_name}"
				row['view_report'] = f"""<a href='{url}' target="_blank" style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'>View Daybook Engineering</a>"""
				# row['view_report'] = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
				# 	target="_blank" company='{filters.get('company')}' from_date='{year_start_date}' to_date='{year_end_date}' account='{account_name}'
				# 	onClick=open_daybook_engineering_report(this.getAttribute('company'),this.getAttribute('from_date'),this.getAttribute('to_date'),this.getAttribute('account'))>View Daybook Engineering</button>"""
	# Finbyz Changes END

	if net_profit_loss:
		data.append(net_profit_loss)

	columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

	chart = get_chart_data(filters, columns, income, expense, net_profit_loss)
	# Finbyz Changes START
	columns.append({
		"fieldname": "view_report",
		"label": _("View Report"),
		"fieldtype": "button",
		"width": 120        
	})
	# Finbyz Changes END

	return columns, data, None, chart

def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
	total = 0
	net_profit_loss = {
		"account_name": "'" + _("Profit for the year") + "'",
		"account": "'" + _("Profit for the year") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value('Company',  company,  "default_currency")
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		total_income = flt(income[-2][key], 3) if income else 0
		total_expense = flt(expense[-2][key], 3) if expense else 0

		net_profit_loss[key] = total_income - total_expense

		if net_profit_loss[key]:
			has_value=True

		total += flt(net_profit_loss[key])
		net_profit_loss["total"] = total

	if has_value:
		return net_profit_loss

def get_chart_data(filters, columns, income, expense, net_profit_loss):
	labels = [d.get("label") for d in columns[2:]]

	income_data, expense_data, net_profit = [], [], []

	for p in columns[2:]:
		if income:
			income_data.append(income[-2].get(p.get("fieldname")))
		if expense:
			expense_data.append(expense[-2].get(p.get("fieldname")))
		if net_profit_loss:
			net_profit.append(net_profit_loss.get(p.get("fieldname")))

	datasets = []
	if income_data:
		datasets.append({'name': _('Income'), 'values': income_data})
	if expense_data:
		datasets.append({'name': _('Expense'), 'values': expense_data})
	if net_profit:
		datasets.append({'name': _('Net Profit/Loss'), 'values': net_profit})

	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}

	if not filters.accumulated_values:
		chart["type"] = "bar"
	else:
		chart["type"] = "line"

	chart["fieldtype"] = "Currency"

	return chart
