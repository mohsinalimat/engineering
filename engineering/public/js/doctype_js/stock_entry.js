cur_frm.fields_dict.job_work_company.get_query = function (doc) {
	return {
		filters: {
			"authority": doc.authority,
			"name": ["!=", doc.company]
		}
	}
};
cur_frm.fields_dict.from_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group": 0
		}
	}
};


cur_frm.fields_dict.to_company_receive_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": ["in", doc.job_work_company],
			"is_group": 0
		}
	}
};

cur_frm.fields_dict.to_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group": 0
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
cur_frm.fields_dict.items.grid.get_field("s_warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group": 0
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group": 0
		}
	}
};


function removeFromArray(original, remove) {
	return original.filter(value => !remove.includes(value));
} 
frappe.ui.form.on('Stock Entry', {
	refresh: (frm) => {
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			if (frm.doc.se_ref && frm.doc.jw_ref){
				if (frm.doc.stock_entry_type == "Send to Jobwork" && frm.doc.authority == "Unauthorized"){
					frm.set_value("se_ref", null);
					frm.set_value("jw_ref", null);
				}
			} else {
				frm.set_value("se_ref", null);
				frm.set_value("jw_ref", null);
			}
		};
		if(frm.doc.docstatus == 1){
			frm.add_custom_button(__("Rate Diff"), function(){
				frappe.call({
					method:"engineering.engineering.doc_events.stock_entry.check_rate_diff",
					args:{
						"doctype":frm.doc.doctype,
						"docname":frm.doc.name
					},
					callback: function(r){
					}
				})
			})
		}
	},
	remove_barcode: function(frm){
		if(frm.doc.remove_barcode) {
			var scan_barcode_field = frm.fields_dict["remove_barcode"]
			frappe.call({
				method: "engineering.override_default_class_method.search_serial_or_batch_or_barcode_number",
				args: { search_value: frm.doc.remove_barcode },
				callback: function(r){
					
					if (r.message.item_code){
						let data = r.message;
						(frm.doc.items || []).forEach(function(item, idx) {
							if (data.item_code == item.item_code){
								let serial_no = item.serial_no
								var ks = serial_no.split(/\r?\n/);
								let remove_serial_no = data.serial_no
								var rm = remove_serial_no.split(/\r?\n/);
								var final = removeFromArray(ks, rm)
								frappe.model.set_value(item.doctype, item.name, 'serial_no', final.join('\n'));
								frappe.model.set_value(item.doctype, item.name, 'qty', final.length);	
								frappe.show_alert({message:__("{0} Pcs removed for item {1}", [data.no_of_items||1,data.item_code]), indicator:'red'});
								
							}
						});
						scan_barcode_field.set_value('');
					} else {
						scan_barcode_field.set_new_description(__('Cannot find Item with this barcode'));
					}
				}
			});
		}
	}

});
erpnext.stock.StockController = erpnext.stock.StockController.extend({
	onload: function () {
		// warehouse query if company
		// Finbyz changes: Override default warehouse filter
		if (this.frm.fields_dict.company) {
			var me = this;
			// erpnext.queries.setup_queries(this.frm, "Warehouse", function (doc) {
			// 	return {
			// 		filters: [
			// 			["Warehouse", "company", "in", ["", cstr(doc.company)]],
			// 			["Warehouse", "is_group", "=", 0]

			// 		]
			// 	}
			// });
		}
	},
	scan_barcode: function(){
		let scan_barcode_field = this.frm.fields_dict["scan_barcode"];

		let show_description = function(idx, exist = null) {
			if (exist) {
				scan_barcode_field.set_new_description(__('Row #{0}: Qty increased by 1', [idx]));
			} else {
				scan_barcode_field.set_new_description(__('Row #{0}: Item added', [idx]));
			}
		};

		let doc = this.frm.doc;
		let frm = this.frm;
		if(this.frm.doc.scan_barcode) {
			frappe.call({
				method: "engineering.override_default_class_method.search_serial_or_batch_or_barcode_number",
				args: { search_value: this.frm.doc.scan_barcode },
				callback: function(r){					 
					if (r.message.item_code){
						let data = r.message;
						var flag = false;
						(doc.items || []).forEach(function(item, idx) {
							if (data.item_code == item.item_code){
								let serial_no = item.serial_no + '\n' + data.serial_no;
								var ks = serial_no.split(/\r?\n/);
								var unique = ks.filter((v, i, a) => a.indexOf(v) === i).sort()
								var i = unique.indexOf("null")
								delete unique[i];
								var i = unique.indexOf("undefined")
								delete unique[i];
								unique  = unique.filter(item => item);
								frappe.db.get_value("Serial No",data.serial_no.split('\n')[0],'warehouse', function(r){
									if (r.warehouse != item.s_warehouse){
										frappe.msgprint("Row: " + item.idx + " Warehouse is Different in this Serial No: " + data.serial_no.split('\n')[0])
									}
								})
								frappe.model.set_value(item.doctype, item.name, 'serial_no', unique.join('\n'));
								frappe.model.set_value(item.doctype, item.name, 'qty', unique.length);
								flag = true
								frappe.show_alert({message:__("Total Qty - {0} : {1} Pcs added for item {2}", [item.qty,data.no_of_items,data.item_code]), indicator:'green'});
							}
						});
						if (flag == false){
							let d =frm.add_child('items');
							frappe.model.set_value(d.doctype, d.name, 'item_code', data.item_code);
							frappe.model.set_value(d.doctype, d.name, 'serial_no', data.serial_no);
							frappe.model.set_value(d.doctype, d.name, 'qty', data.no_of_items);
							frappe.show_alert({message:__("Total Qty - {0} : {1} Pcs added for item {2}", [item.qty,data.no_of_items||1,data.item_code]), indicator:'green'});
							frm.refresh_field('items');
						}

						scan_barcode_field.set_value('');
					} else {
						scan_barcode_field.set_new_description(__('Cannot find Item with this barcode'));
					}
				}
			});
		}
		// return false;
	},

	setup_warehouse_query: function () {
		
	},
    show_stock_ledger: function () {
        var me = this;
        if (this.frm.doc.docstatus === 1) {
            cur_frm.add_custom_button(__("Stock Ledger Engineering"), function () {
                frappe.route_options = {
                    voucher_no: me.frm.doc.name,
                    from_date: me.frm.doc.posting_date,
                    to_date: me.frm.doc.posting_date,
                    company: me.frm.doc.company
                };
                frappe.set_route("query-report", "Stock Ledger Engineering");
            }, __("View"));
        }

    },
})

erpnext.show_serial_batch_selector = function(frm, d, callback, on_close, show_dialog) {
	frappe.require("assets/engineering/js/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: d,
			warehouse_details: {
				type: "Warehouse",
				name: d.s_warehouse
			},
			callback: callback,
			on_close: on_close
		}, show_dialog);
	});
}
$.extend(cur_frm.cscript, new erpnext.stock.StockController({ frm: cur_frm }));
