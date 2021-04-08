frappe.require("assets/erpnext/js/financial_statements.js", function() {
	frappe.query_reports["Item Groupwise Stock Balance"] = {
		"filters": [
			{
				"fieldname": "company",
				"label": __("Company"),
				"fieldtype": "Link",
				"options": "Company",
				"default": frappe.defaults.get_user_default("Company"),
				"reqd": 1
			},
			{
				"fieldname":"warehouse",
				"label": __("Warehouse"),
				"fieldtype": "Link",
				"options": "Warehouse",
				"get_query": function() {
					const company = frappe.query_report.get_filter_value('company');
					return { 
						filters: { 'company': company }
					}
				}
			},
			{
				"fieldname":"authorized",
				"label": __("Authorized"),
				"fieldtype": "Check",				
			},
			{
				"fieldname":"unauthorized",
				"label": __("Unauthorized"),
				"fieldtype": "Check",				
			}

		],
		"tree": true,
		"name_field": "item_group",
		"parent_field": "parent_item_group",
		"initial_depth": 1,
		"formatter": function(value, row, column, data, default_formatter) {
			if (column.fieldname=="item_group") {
				value = data.item_group || value;
	
				column.link_onclick =
					"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
				column.is_tree = true;
			}
	
			value = default_formatter(value, row, column, data);
	
			if (!data.parent_item_group) {
				value = $(`<span>${value}</span>`);
	
				var $value = $(value).css("font-weight", "bold");
				if (data.warn_if_negative && data[column.fieldname] < 0) {
					$value.addClass("text-danger");
				}
	
				value = $value.wrap("<p></p>").parent().html();
			}
	
			return value;
		},
	}
});

// function route_to_sbe(company,item_group){

// 	frappe.set_route("query-report", "Stock Ledger Engineering",{
// 		"company": company,
// 		"item_group": item_group
	
// 	});
// }
// function route_to_sle_item(company, item_name ){
// 	// frappe.route_options = {
// 	// 	item_group: me.frm.doc.item_group,
// 	// 	company: me.frm.doc.company
// 	// };
// 	frappe.set_route("query-report", "Stock Ledger Engineering",{
// 		"company": company,
// 		"item_code": item_name
// 	}); "item_code=" + item_name
// }

function route_to_sle(company, item_group) {
	window.open(window.location.href.split("#")[0] + "#query-report/Stock Ledger Engineering" + "/?" + "company=" + company + "&" +  "item_group="+item_group,"_blank")	
}

function route_to_stock_balance(company, item_group) {
	window.open(window.location.href.split("#")[0] + "#query-report/Stock Balance Engineering" + "/?" + "company=" + company + "&" +  "item_group="+item_group,"_blank")	
}

function route_to_sle_item(company, item_name) {
	window.open(window.location.href.split("#")[0] + "#query-report/Stock Ledger Engineering" + "/?" + "company="+company + "&" + "item_code=" + item_name,"_blank")	
}

function route_to_stock_balance_item(company, item_name) {
	window.open(window.location.href.split("#")[0] + "#query-report/Stock Balance Engineering" + "/?" + "company="+company + "&" + "item_code=" + item_name,"_blank")	
}