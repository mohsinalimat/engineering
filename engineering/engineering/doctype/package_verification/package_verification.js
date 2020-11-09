// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.to_company_receive_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": ["in", doc.company],
			"is_group": 0
		}
	}
};

frappe.ui.form.on('Package Verification', {
	onload: function(frm){
		frm.trigger('create_stock_entry')
	},
	refresh: function(frm){
		frm.trigger('create_stock_entry')
	},
	validate: function(frm){
		frm.doc.packages_detail.forEach(function(row){
			console.log('called')
			frappe.call({
				method:"engineering.engineering.doctype.package_verification.package_verification.get_serial_nos",
				args:{
					"serial_no" : row.serial_no,
				},
				callback:function(r){
					frappe.db.get_value("Serial No",r.message,['company','warehouse','status'],function(r){
						frappe.model.set_value(row.doctype,row.name,'company',r.company)
						frappe.model.set_value(row.doctype,row.name,'warehouse',r.warehouse)
						frappe.model.set_value(row.doctype,row.name,'status',r.status)
					})
				}
			})
		})
	},
	create_stock_entry: function(frm){
				if (frm.doc.docstatus == 1 || frm.doc.docstatus==0){
		
					frm.add_custom_button("Create Stock Entry", function() {
						frappe.call({
							method: "engineering.engineering.doctype.package_verification.package_verification.create_stock_entry",
							args:{
								"name":frm.doc.name
							},
							freeze:true,
							callback:function(r){

							}
						})
					})
				}

	},
	package: function(frm){
		let package_field = frm.fields_dict["package"];

		let doc = frm.doc;
		if(frm.doc.package) {
			frappe.call({
				method: "engineering.override_default_class_method.search_serial_or_batch_or_barcode_number",
				args: { search_value: frm.doc.package },
				callback: function(r){
					if (r.message.item_code){
						var flag = 1;
							(doc.packages_detail || []).forEach(function(item, idx){
								if (item.package == frm.doc.package){
									package_field.set_new_description(__('Package is already exists in Packages Detail'));
									flag = 0;
								}
							})
						
						if(flag == 1){
							let d =frm.add_child('packages_detail');
							frappe.model.set_value(d.doctype, d.name, 'package', frm.doc.package);
							frappe.model.set_value(d.doctype, d.name, 'item_code', r.message.item_code);
							frappe.model.set_value(d.doctype, d.name, 'serial_no', r.message.serial_no);
							frappe.model.set_value(d.doctype, d.name, 'no_of_items',r.message.no_of_items);
							
							frm.refresh_field('packages_detail');
	
							package_field.set_value('');
						}
					} else {
						package_field.set_new_description(__('Cannot find Item with this barcode'));
					}
				}
			});
		}
		// return false;
		frm.trigger('serial_no')
	},
});
frappe.ui.form.on('Package Verification Detail', {
	serial_no: function(frm,cdt,cdn){
		console.log('called in serial')
		var d = locals[cdt][cdn]
		frappe.call({
			method:"engineering.engineering.doctype.package_verification.package_verification.get_serial_nos",
			args:{
				"serial_no" : d.serial_no,
			},
			callback:function(r){
				frappe.db.get_value("Serial No",r.message,['company','warehouse','status'],function(r){
					frappe.model.set_value(d.doctype,d.name,'company',r.company)
					frappe.model.set_value(d.doctype,d.name,'warehouse',r.warehouse)
					frappe.model.set_value(d.doctype,d.name,'status',r.status)
				})
			
				//frappe.model.set_value(d.doctype,d.name,'company',)
			}
		})
	},
});
