cur_frm.fields_dict.job_work_company.get_query = function (doc) {
	return {
		filters: {
			"authority": doc.authority
		}
	}
};
cur_frm.fields_dict.finish_item.get_query = function (doc) {
	return {
		filters: {
			"is_stock_item": 1
		}
	}
};

frappe.ui.form.on('Stock Entry', {
	on_submit: function(frm){
		frappe.run_serially([ 

			() => {
				if (frm.doc.docstatus == 1 && frm.doc.jw_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_stock_entry',
						async: false,
						args: {
							'name': frm.doc.jw_ref
						},
						callback: function (r) {
							frappe.msgprint("Submitted");
						}
					})
				}
			},
			() => {
				if (frm.doc.docstatus == 1 && frm.doc.se_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_stock_entry',
						async: false,
						args: {
							'name': frm.doc.se_ref,
						},
						callback: function (r) {
							if (r.message){
								frappe.call({
									method: 'engineering.engineering.doc_events.stock_entry.submit_stock_entry',
									async: false,
									args: {
										'name': r.message
									},
									callback: function (r) {
										
									}
								})
							}
						}
					})
				}
			}
		])

		
	}
});