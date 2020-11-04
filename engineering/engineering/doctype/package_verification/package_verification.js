// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Package Verification', {
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

	}
});
