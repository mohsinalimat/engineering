frappe.ui.form.on('Salary Slip', {
    employee: function(frm) {
		frm.trigger("get_detail");
	},
	get_detail: function(frm) {
		if (frm.doc.employee) {
			frappe.call({
				method: "erpnext.hr.doctype.leave_application.leave_application.get_leave_details",
				async: false,
				args: {
					employee: frm.doc.employee,
					date: frm.doc.start_date || frm.doc.posting_date
				},
				callback: function(r) {
				    frm.doc.leave_detail = []
				    for (const [key, value] of Object.entries(r.message['leave_allocation'])) {
				        var row = frm.add_child("leave_detail");
				        row.leave_type = key;
				        row.total_leaves = value['total_leaves'];
				        row.expired_leaves = value['expired_leaves'];
				        row.leaves_taken = value['leaves_taken'];
				        row.pending_leaves = value['pending_leaves'];
				        row.remaining_leaves = value['remaining_leaves'];
                    }
				
					refresh_field("leave_detail");
				}
			});
		
		}
	},
})