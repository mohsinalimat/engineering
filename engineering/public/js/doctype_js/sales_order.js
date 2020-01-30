frappe.ui.form.on('Sales Order', {
	onload: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
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