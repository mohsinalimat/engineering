cur_frm.fields_dict.item_series.get_query = function(doc) {
	return {
		filters: {
			"authority": "Authorized",
		}
	}
};
frappe.ui.form.on("Item", {
    refresh: function(frm) {
        frm.remove_custom_button("Ledger", "View");
        if (frm.doc.is_stock_item) {
            frm.add_custom_button(__("Stock Ledger Engineering"), function() {
                frappe.route_options = {
                    item_code : frm.doc.name
                }
                frappe.set_route("query-report", "Stock Ledger Engineering");
            }, __("View"));
        }
    },
});