frappe.ui.form.on('Payment Entry', {
	refresh: function(frm){
		if (frm.doc.__islocal){
			if (cur_frm.doc.company){
				frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
					frm.set_value('company_series', r.company_series);
				});
			}
			if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
				console.log("Hi")
				if ((frm.doc.pe_ref) || (!frm.doc.pe_ref && frm.doc.branch_pay_pe_ref && frm.doc.branch_receive_pe_ref)){
					frm.set_value('pe_ref', null);
					frm.set_value('branch_pay_pe_ref', null);
					frm.set_value('branch_receive_pe_ref', null);
				}
			}
			frm.trigger('company');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from && frm.doc.__islocal){
			frappe.call({
				method: "engineering.api.check_counter_series",
				args: {
					'name': frm.doc.naming_series,
					'company_series': frm.doc.company_series,
				},
				callback: function(e) {
					frm.set_value("series_value", e.message);
				}
			});
		}
	},
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	}
});