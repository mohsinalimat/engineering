// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */
var d = new Date();
var dt = new Date(d.getFullYear(),d.getMonth(),1);
frappe.query_reports["Stock Balance Engineering"] = {
	onload: function(report){
		frappe.call({
			method:"engineering.engineering.report.stock_balance_engineering.stock_balance_engineering.validate_filters",
			args:filters,
		})
	},
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Company",
			"default": frappe.defaults.get_default("company"),
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 1,
			"default": dt
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
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item Group"
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Item",
			"get_query": function() {
				return {
					query: "erpnext.controllers.queries.item_query",
				};
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse",
			"get_query": function() {
				const company = frappe.query_report.get_filter_value('company');
				return { 
					filters: { 'company': company }
				}
			},
			"hidden":1,
			
		},
		{
			"fieldname": "warehouse_type",
			"label": __("Warehouse Type"),
			"fieldtype": "Link",
			"width": "80",
			"options": "Warehouse Type",
			"hidden":1
		},
		{
			"fieldname":"include_uom",
			"label": __("Include UOM"),
			"fieldtype": "Link",
			"options": "UOM"
		},
		{
			"fieldname": "show_variant_attributes",
			"label": __("Show Variant Attributes"),
			"fieldtype": "Check"
		},
		{
			"fieldname": 'show_stock_ageing_data',
			"label": __('Show Stock Ageing Data'),
			"fieldtype": 'Check'
		},
		{
			"fieldname": 'show_rate_value',
			"label": __('Show Rate Value'),
			"fieldtype": 'Check'
		},
		{
			"fieldname": 'show_reorder_details',
			"label": __('Show Reorder Details'),
			"fieldtype": 'Check'
		},
		{
			"fieldname": 'show_0_qty_inventory',
			"label": __('Show 0 Qty Inventory'),
			"fieldtype": 'Check'
		},
		{
			"fieldname":"show_internal_transfers",
			"label": __("Show Internal Transfers"),
			"fieldtype": "Check",
		},
		{
			"fieldname":"show_warehouse_wise_balance",
			"label": __("Show Warehouse Wise Balance"),
			"fieldtype": "Check",
			"on_change": function(){
				if (frappe.query_report.get_filter_value('show_warehouse_wise_balance')){
					frappe.query_report.get_filter('warehouse').toggle(true)
					frappe.query_report.get_filter('warehouse_type').toggle(true)
				}
				else{
					frappe.query_report.get_filter('warehouse').toggle(false)
					frappe.query_report.get_filter('warehouse_type').toggle(false)
				}
				frappe.query_report.refresh();

		}
	},

	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname == "out_qty" && data && data.out_qty > 0) {
			value = "<span style='color:red'>" + value + "</span>";
		}
		else if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
			value = "<span style='color:green'>" + value + "</span>";
		}

		return value;
	}
};
function view_stock_leder_report(item_code, company, warehouse,from_date, to_date) {
	window.open(window.location.href.split('app')[0] + "app/query-report/Stock Ledger Engineering" + "/?" + "item_code=" + item_code + "&" +  "company="+company + "&" + "warehouse=" + warehouse + "&" +  "from_date=" + from_date + "&" + "to_date=" + to_date,"_blank")	
}