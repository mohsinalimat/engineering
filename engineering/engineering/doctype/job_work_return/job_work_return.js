// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.material_transfer.get_query = function (doc) {
	return {
		filters: {
			"purpose": 'Material Transfer',
			"stock_entry_type": 'Send to Jobwork',
			"docstatus": 1,
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.item_code.get_query = function (doc) {
	return {
		filters: {
			"is_stock_item": 1
		}
	}
};
cur_frm.fields_dict.bom_no.get_query = function (doc) {
	return {
		filters: {
			"item": doc.item_code
		}
	}
};
cur_frm.fields_dict.t_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.s_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc, cdt, cdn) {
    var d = locals[cdt][cdn];
    return {
    	filters: {
        	"company": doc.company
    	}
    }
};
frappe.ui.form.on('Job Work Return', {
	bom_no: function (frm) {
		frm.set_value("qty", "");
		frm.doc.items = [];
		refresh_field('items');
	},
	qty: function (frm) {
		frm.doc.items = [];
		refresh_field('items');
		if (frm.doc.bom_no != "") {
			frappe.model.with_doc("BOM", frm.doc.bom_no, function () {
				var os_doc = frappe.model.get_doc("BOM", frm.doc.bom_no);

				$.each(os_doc.items, function (index, row) {
					let d = frm.add_child("items");

					d.item_code = row.item_code;
					d.item_name = row.item_name;
					d.uom = row.uom;
					d.basic_rate = row.rate;
					d.qty = flt(flt(frm.doc.qty * row.qty) / os_doc.quantity);
					d.amount = d.basic_rate * d.qty;
				});
				frm.refresh_field('items');
			});
		}
	},
	on_submit1: function (frm) {
		frappe.run_serially([
			() => {
				if (frm.doc.docstatus == 1 && frm.doc.repack_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
						async: false,
						args: {
							'name': frm.doc.repack_ref
						},
						callback: function (r) {
							if (r.message){
								frappe.call({
									method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
									async: false,
									args: {
										'name': r.message
									},
									callback: function (r) {
										frappe.msgprint("Submitted");
									}
								});
							}
						}
					});
				}
			},
			() => {
				if (frm.doc.docstatus == 1 && frm.doc.issue_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
						async: false,
						args: {
							'name': frm.doc.issue_ref,
						},
						callback: function (r) {
							if (r.message){
								frappe.call({
									method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
									async: false,
									args: {
										'name': r.message
									},
									callback: function (r) {
										frappe.msgprint("Submitted");
									}
								});
							}
						}
					})
				}
			}
		])
	}
});
