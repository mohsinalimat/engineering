frappe.ui.form.on('Work Order', {
	refresh: function(frm) {

		//cur_frm.clear_custom_buttons();
		frm.trigger('create_material_request')

		$(".form-inner-toolbar").find("button[data-label=Finish]").css({ "float": "right" })
		if (frm.doc.status != 'Completed' && !frm.doc.skip_transfer && frm.doc.docstatus == 1) {
			var transfer_btn = frm.add_custom_button(__('Transfer Material'), function () {
				erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
			});
			transfer_btn.addClass('btn-primary');
		}
		cur_frm.custom_make_buttons = {}
	},
	wip_warehouse: function (frm) {
	    frm.trigger('set_sales_warehouse')
	},
	set_sales_warehouse: function (frm) {
	    frm.doc.required_items.forEach(function (d) {
			frappe.model.set_value(d.doctype, d.name, 'source_warehouse', frm.doc.source_warehouse);
		});
	},
	create_material_request: function(frm) {
		frm.add_custom_button(__('Create Material Request'), () => {
			frappe.model.open_mapped_doc({
				method: "engineering.engineering.doc_events.work_order.create_material_request",
				frm: frm
			});
		});
	}
});

frappe.ui.form.on('Work Order Item', {
	item_code(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		
		frappe.model.set_value(d.doctype, d.docname, 'include_item_in_manufacturing', 1)
	},

    required_items_add: function(frm, cdt, cdn){
		var row = locals[cdt][cdn];
		row.source_warehouse = frm.doc.wip_warehouse;
		frappe.model.set_value(cdt, cdn, 'source_warehouse', frm.doc.source_warehouse)
		frm.refresh_field("required_items");
	},
})