// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt
cur_frm.fields_dict.warehouse.get_query = function(doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};

cur_frm.fields_dict.work_order.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 1,
			"production_item": doc.item_code,
			"status": "In Process"
		}
	}
};

frappe.ui.form.on('Item Packing', {
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
	},
	add_serial_no: function(frm){
		if (frm.doc.add_serial_no){
			if (frm.doc.serial_no){
				var ks = frm.doc.serial_no.split(/\r?\n/);
				ks.push(frm.doc.add_serial_no)
				var unique = ks.filter((v, i, a) => a.indexOf(v) === i).sort();
				if (unique.length <= frm.doc.qty_per_box){
					frm.set_value("serial_no", unique.join('\n'))
				} else {
					frm.set_value("add_serial_no", null)
					frappe.throw("Serial No Per Box Can not be greater than " + frm.doc.qty_per_box + '.')
				}
			} else {
				frm.set_value("serial_no", frm.doc.add_serial_no)
			}
			frm.set_value("add_serial_no", null)
		}
	},
	remove_serial_no: function(frm){
		if (frm.doc.remove_serial_no){
			if (frm.doc.serial_no){
				var ks = frm.doc.serial_no.split(/\r?\n/);
				for(var i = ks.length - 1; i >= 0; i--) {
					if(ks[i] === frm.doc.remove_serial_no) {
						ks.splice(i, 1);
						break;
					}
				}
				var unique = ks.filter((v, i, a) => a.indexOf(v) === i).sort();
				frm.set_value("serial_no", unique.join('\n'));
			}
			frm.set_value("remove_serial_no", null)
		}
	}
});


// frappe.ui.form.on('Item Packing', {
// 	// refresh: function(frm) {

// 	// }
// });

frappe.ui.keys.on('ctrl+p', function(e) {
	// Your Code
	// cur_frm.get_field('qc6').$input.focus();
	try {
		if (cur_frm.doc.doctype == "Item Packing"){
			e.preventDefault();
			
			frappe.run_serially([
			// () => {
			// 	if (cur_frm.doc.docstatus != 1){
			// 		cur_frm.save();
			// 		console.log("Function 1")
			// 	}
			// },
			// () => {
			// 	cur_frm.reload_doc();
			// 	console.log("Function 2")
			// 	console.log(cur_frm.doc.name)
			// },
			() => {
				cur_frm.call({
					doc: cur_frm.doc,
					method: 'print_package',
					callback: function(r) {
						var w = window.open(frappe.urllib.get_full_url("/printview?"
						+ "doctype=" + encodeURIComponent("Item Packing")
						+ "&name=" + encodeURIComponent(r.message)
						+ ("&trigger_print=1")
						+ "&format=" + encodeURIComponent("Package Sticker")));
	
						if (!w) {
							frappe.msgprint(__("Please enable pop-ups")); return;
						}
						cur_frm.doc.serial_no = '';
						cur_frm.doc.series_value += 1
						cur_frm.refresh()
						$("[data-fieldname=add_serial_no]").focus()
					}
				});
			}
			]);
			return false;
		}
	} catch{

	}
});