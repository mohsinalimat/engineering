// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Unverified Package"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd":1,
			"default": frappe.defaults.get_user_default("Company")
		},
	]
};
