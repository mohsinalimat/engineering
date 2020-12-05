// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Profit and Loss Statement Engineering"] = $.extend({},
		erpnext.financial_statements);

	erpnext.utils.add_dimensions('Profit and Loss Statement Engineering', 10);

	frappe.query_reports["Profit and Loss Statement Engineering"]["filters"].push(
		{
			"fieldname": "project",
			"label": __("Project"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Project', txt);
			}
		},
		{
			"fieldname": "accumulated_values",
			"label": __("Accumulated Values"),
			"fieldtype": "Check"
		},
		{
			"fieldname": "include_default_book_entries",
			"label": __("Include Default Book Entries"),
			"fieldtype": "Check",
			"default": 1
		}
	);
});

function open_report(company, account_show_report) {
	window.open(window.location.href.split("#")[0] + "#query-report/" + account_show_report + "/?" + "company="+company,"_blank")	
}
function open_daybook_engineering_report(company,from_date,to_date,account) {
	window.open(window.location.href.split("#")[0] + "#query-report/Daybook Engineering" + "/?" + "company="+company +"&" +  "from_date="+from_date +"&"+ "to_date="+to_date +"&"+ "account="+account,"_blank")	
}