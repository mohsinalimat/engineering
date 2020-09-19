// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial No Generator', {
	// refresh: function(frm) {

	// }
	series: function(frm){
		frm.trigger("append");
	},
	
	append: function(frm){
		if (frm.doc.series){
			frappe.call({
				method: "engineering.api.get_serial_no_series",
					args: {
						'name':frm.doc.series,
						'posting_date': frm.doc.posting_date,
					},
	
				callback: function(e){
					frm.set_value("serial_no_series",e.message);
	
				}
			});
		}
	},
	
	validate: function(frm){
		frm.trigger("append");
	},

	serial_no_series: function(frm) {
		if ( !frm.doc.amended_from){
			frappe.call({
				method: "engineering.api.check_counter_series",
				args: {
					'name': frm.doc.serial_no_series,
				},
				callback: function(e) {
					frm.set_value("from_value", e.message);
				}
			});
		}
	},


});
