// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt
cur_frm.fields_dict.box_item.get_query = function(doc) {
	return {
		filters: {
			"is_box_item": 1,
		}
	}
};


frappe.ui.form.on('Item Packing', {
	// refresh: function(frm) {

	// }
});

frappe.ui.keys.on('ctrl+p', function(e) {
	// Your Code
	// cur_frm.get_field('qc6').$input.focus();
	e.preventDefault();
	if (cur_frm.doc.docstatus != 1){
		cur_frm.save();
	}
	return false;
});