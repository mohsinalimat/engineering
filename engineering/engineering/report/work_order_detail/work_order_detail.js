// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Work Order Detail"] = {
	"filters": [
        {
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"production_item",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"reqd": 0
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("company")
		}
	]
};