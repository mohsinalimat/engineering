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
	refresh: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('auto_create_serial_no')
		}
		if (frm.doc.docstatus == 1 && frm.doc.work_order && !frm.doc.stock_entry){
			frm.add_custom_button("Make Manufacture Entry", function() {
				setTimeout(() => {
					frm.remove_custom_button('Make Manufacture Entry');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.item_packing.item_packing.enqueue_stock_entry",
					args: {
						'work_order': frm.doc.work_order,
						'posting_date': frm.doc.posting_date,
						'posting_time': frm.doc.posting_time
					},
					freeze: true,
					callback: function(r){
						if (r.message){
							frappe.msgprint(r.message);
						}
					}
				})
			})
		}
		if (!frm.doc.work_order && frm.doc.docstatus == 1 && !frm.doc.stock_entry){
			frm.add_custom_button('Make Material Receipt', function() {
				if (!frm.doc.warehouse){
					frappe.throw("Please Enter Warehouse")
				}
				setTimeout(() => {
					frm.remove_custom_button('Make Material Receipt');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.item_packing.item_packing.enqueue_material_receipt",
					args: {
						'warehouse': frm.doc.warehouse,
						'item_code': frm.doc.item_code,
						'company': frm.doc.company,
						'posting_date': frm.doc.posting_date,
						'posting_time': frm.doc.posting_time
					},
					freeze: true,
					callback: function(r){
						if (r.message){
							frappe.msgprint(r.message)
						}
					}
				})
			})
		}
	},
	onload: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
			frm.trigger('auto_create_serial_no')
		}
	},
	before_save: function (frm) {
		frm.trigger('cal_wt')
	},
	work_order: function(frm){
		if(frm.doc.work_order){
			frappe.call({
				method: "engineering.engineering.doctype.item_packing.item_packing.get_work_order_manufactured_qty",
				args: {
					'work_order': frm.doc.work_order
				},
				callback: function(r){
					frm.set_value('no_of_item_work_order', r.message)
				}
			})
		}
	},
	auto_create_serial_no: function(frm){
		if(frm.doc.auto_create_serial_no){
			frm.set_df_property("serial_no", "reqd", 0);
		}
		else{
			frm.set_df_property("serial_no", "reqd", 1);
		}
	},
	// cal_wt: function(frm){
	// 	frappe.db.get_value("Item", frm.doc.item_code,'weight_per_unit', function (r) {
	// 		console.log('weight_per_unit')
	// 		if (r.weight_per_unit){
	// 			frappe.model.set_value(frm.doctype,frm.name, 'net_wt', flt((frm.doc.no_of_items)*(r.weight_per_unit)));
	// 			console.log('net_wt')
	// 			frappe.db.get_value("Item", frm.doc.packing_item,'weight_per_unit', function (d) {
	// 				if(d.weight_per_unit){
	// 					frappe.model.set_value(frm.doctype,frm.name, 'gross_wt', flt(((frm.doc.no_of_items)*(r.weight_per_unit))+ d.weight_per_unit));
	// 					console.log('gross_wt')
	// 				}

	// 			})
	// 		}

	// })
	// },
	cal_wt: function(frm){
		frappe.db.get_value("Item", frm.doc.item_code,'weight_per_unit', function (r) {
			if (r.weight_per_unit){
				frm.set_value('net_wt', flt((frm.doc.no_of_items)*(r.weight_per_unit)));
				// console.log((frm.doc.net_wt))
			}
		frappe.db.get_value("Item", frm.doc.packing_item,'weight_per_unit', function (d) {
			if (d.weight_per_unit){
				frm.set_value('gross_wt',flt(((frm.doc.no_of_items)*(r.weight_per_unit))+ d.weight_per_unit));
				// console.log((frm.doc.gross_wt))
			
			}
				})
			})
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
					frm.set_value("no_of_items", unique.length);
				} else {
					frm.set_value("add_serial_no", null)
					frappe.throw("Serial No Per Box Can not be greater than " + frm.doc.qty_per_box + '.')
				}
			} else {
				frm.set_value("serial_no", frm.doc.add_serial_no)
				frm.set_value("no_of_items", 1);
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
				frm.set_value("no_of_items", unique.length);
				frm.set_value("serial_no", unique.join('\n'));
			}
			frm.set_value("remove_serial_no", null)
		}
	}
});


// frappe.ui.form.on('Item Packing', {
// 	cal_wt: function(frm){
// 		frappe.db.get_value("Item", frm.doc.item_code,'weight_per_unit', function (r) {
// 			if (r.weight_per_unit){
// 				frappe.model.set_value(frm.doctype,frm.name, 'net_wt', flt((frm.doc.no_of_items)*(r.weight_per_unit)));
// 				frappe.db.get_value("Item", frm.doc.packing_item,'weight_per_unit', function (d) {
// 					if(d.weight_per_unit){
// 						frappe.model.set_value(frm.doctype,frm.name, 'gross_wt', flt(((frm.doc.no_of_items)*(r.weight_per_unit))+ d.weight_per_unit));

// 					}

// 				})
// 			}

// 	})
// 	},
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
						if(cur_frm.doc.work_order){
							frappe.call({
								method: "engineering.engineering.doctype.item_packing.item_packing.get_work_order_manufactured_qty",
								args: {
									'work_order': cur_frm.doc.work_order
								},
								callback: function(r){
									cur_frm.set_value('no_of_item_work_order', r.message)
								}
							})
						}
						cur_frm.doc.serial_no = '';
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