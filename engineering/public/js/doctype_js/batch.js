frappe.ui.form.on("Batch", {
    refresh: function(frm) {
        frm.remove_custom_button("View Ledger");
        if(!frm.is_new()) {
			frm.add_custom_button(__("View Engineering Ledger"), () => {
				frappe.route_options = {
					batch_no: frm.doc.name
				};
				frappe.set_route("query-report", "Stock Ledger Engineering");
			});
			frm.trigger('make_dashboard');
        }
    },
});
