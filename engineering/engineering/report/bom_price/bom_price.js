// Copyright (c) 2016, FinByz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["BOM Price"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"price_list",
			"label":__("Price List"),
			"fieldtype":"Link",
			"options":"Price List",
		},
		{
			"fieldname":"rm_cost_based_on",
			"label":__("Rate Of Materials Based On"),
			"fieldtype":"Select",
			"options":"Price List\nValuation Rate\nLast Purchase Rate",
			"default":"Price List"
		},
		{
			"fieldname":"show_0_qty_data",
			"label":__("Show 0 Qty Data"),
			"fieldtype":"Check",			
		}
	],
	"tree": true,
	"name_field": "item_group",
	"parent_field": "parent_item_group",
	"initial_depth": 1,
	"formatter": function(value, row, column, data, default_formatter) {
		if (column.fieldname=="item_group") {
			value = data.item_group || value;

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
};
