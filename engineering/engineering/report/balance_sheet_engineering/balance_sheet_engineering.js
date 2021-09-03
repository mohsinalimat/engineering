// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.require("assets/erpnext/js/financial_statements.js", function() {
frappe.query_reports["Balance Sheet Engineering"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions('Balance Sheet Engineering', 10);

	frappe.query_reports["Balance Sheet Engineering"]["filters"].push({
		"fieldname": "accumulated_values",
		"label": __("Accumulated Values"),
		"fieldtype": "Check",
		"default": 1
	});

	frappe.query_reports["Balance Sheet Engineering"]["filters"].push({
		"fieldname": "include_default_book_entries",
		"label": __("Include Default Book Entries"),
		"fieldtype": "Check",
		"default": 1
	});
});

function open_report(company, account_show_report) {
	window.open(window.location.href.split('app')[0] + "app/query-report/" + account_show_report + "/?" + "company="+company,"_blank")	
}
function open_daybook_engineering_report(company,from_date,to_date,account) {
	window.open(window.location.href.split('app')[0] + "app/query-report/Daybook Engineering" + "/?" + "company="+company +"&" +  "from_date="+from_date +"&"+ "to_date="+to_date +"&"+ "account="+account,"_blank")	
}
// function view_account_receivable_report(company) {
// 	window.open(window.location.href.split('app')[0] + "app/query-report/Accounts Receivable Engineering Summary" + "/?" + "company="+company,"_blank")	
// }
// function view_account_payable_report(company) {
// 	window.open(window.location.href.split('app')[0] + "app/query-report/Accounts Payable Engineering Summary" + "/?" + "company="+company,"_blank")	
// }
