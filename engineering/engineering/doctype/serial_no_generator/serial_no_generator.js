// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial No Generator', {
	// refresh: function(frm) {

	// }
	series: function(frm){
		frm.trigger("append");
	},
	append: function(frm){
		frm.set_value("serial_no_series",frm.doc.series.concat("A"))
		
	},

	
	validate: function(frm){
		frm.trigger("append");
	},
});
