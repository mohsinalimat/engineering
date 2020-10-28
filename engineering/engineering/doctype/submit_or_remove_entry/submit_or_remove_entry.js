// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Submit or Remove Entry', {
	refresh: function(frm) {
			cur_frm.page.add_action_item(__("Cancel"), function() {
				frappe.call({
					method:"engineering.engineering.doctype.submit_or_remove_entry.submit_or_remove_entry.enqueue_cancel_entry",
					args:{
						'doc_type':frm.doc.doc_type,
						'doc_name':frm.doc.doc_name
					},
					freeze: true,
					callback:function(r){
					}
				})
			});
			cur_frm.page.add_action_item(__("Submit"), function() {
				frappe.call({
					method:"engineering.engineering.doctype.submit_or_remove_entry.submit_or_remove_entry.enqueue_submit_entry",
					args:{
						'doc_type':frm.doc.doc_type,
						'doc_name':frm.doc.doc_name
					},
					freeze: true,
					callback:function(r){
					}
				})
			});
	}
});
