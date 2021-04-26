this.frm.cscript.onload = function (frm) {
	this.frm.set_query("production_item", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: { 'is_stock_item': 1, 'authority': doc.authority,'production_item':1 }
		}
	});
	this.frm.set_query("item_code", "required_items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_stock_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
}
frappe.ui.form.on('Work Order', {
	setup: function(frm){
		frm.set_indicator_formatter('item_code', function(doc) { return (doc.available_qty_at_source_warehouse>=doc.required_qty) ? "green" : "orange"; });
	},
	refresh: function(frm) {

		//cur_frm.clear_custom_buttons();
		if (frm.doc.status == 'Not Started') {
			frm.trigger('create_material_request')
		}

		$(".form-inner-toolbar").find("button[data-label=Finish]").css({ "float": "right" })
		if (frm.doc.status != 'Completed' && !frm.doc.skip_transfer && frm.doc.docstatus == 1 && frm.doc.material_transferred_for_manufacturing < frm.doc.qty) {
			var transfer_btn = frm.add_custom_button(__('Transfer Material'), function () {
				erpnext.work_order.make_se(frm, 'Material Transfer for Manufacture');
			});
			transfer_btn.addClass('btn-primary');
		}
		$("button[data-label='Start']").css({'display': 'none' })
		cur_frm.custom_make_buttons = {}
	},
	source_warehouse: function (frm) {
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
	},
	update_actual_qty: function (frm) {
		frappe.call({
			method: "engineering.engineering.doc_events.work_order.set_actual_qty_in_wo",
			args: {
				'wo_number': frm.doc.name
			},
			callback: function (r) {
				frappe.msgprint(r.message);
				frm.refresh_fields();
				location.reload();
			}
		})
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
		frappe.model.set_value(cdt, cdn, 'allow_alternative_item', 1)
		frm.refresh_field("required_items");
	},
})