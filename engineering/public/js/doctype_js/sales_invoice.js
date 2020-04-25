erpnext.accounts.SalesInvoiceController = erpnext.accounts.SalesInvoiceController.extend({
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
								let serial_no = item.serial_no + '\n';
								frappe.model.set_value(item.doctype, item.name, 'serial_no', serial_no + data.serial_no);
								flag = true
							}
						});
						if (flag == false){
							let d =frm.add_child('items');
							frappe.model.set_value(d.doctype, d.name, 'item_code', data.item_code);
							frappe.model.set_value(d.doctype, d.name, 'serial_no', data.serial_no);
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
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));
<<<<<<< HEAD
cur_frm.fields_dict.items.grid.get_field("item_code").get_query = function (doc) {
	return {
		filters: {
			"is_sales_item": 1,
			"authority": doc.authority
		}
	}
};
=======
this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: { 'is_sales_item': 1, 'authority': doc.authority }
		}
	});
}
>>>>>>> dde207d12f5ee3be00c5e653906837f14d3cfa5d
frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm){
		frm.page.get_inner_group_button(__("Get items from")).find("button").addClass("hide");
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("ref_si", "");
			frm.set_value("ref_pi", "");
			frm.set_value("inter_company_invoice_reference", "");
			frm.set_value("branch_invoice_ref")
		}
		if (cur_frm.doc.company){
			frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
				frm.set_value('company_series', r.company_series);
			});
		}
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	onload: function(frm){
		frm.page.get_inner_group_button(__("Get items from")).find("button").addClass("hide");
	},
	onload_post_render: function(frm) {
		frm.page.get_inner_group_button(__("Get items from")).find("button").addClass("hide");
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
	},
	company_series: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	on_submit: function(frm){
		if (frm.doc.docstatus == 1 && frm.doc.inter_company_invoice_reference){
			frappe.call({
				method: 'engineering.engineering.doc_events.sales_invoice.submit_purchase_invoice',
				args: {
					'pi_number': frm.doc.inter_company_invoice_reference
				},
				callback: function(r){
					frappe.msgprint("Submitted")
				}
			})
		}
	}
});