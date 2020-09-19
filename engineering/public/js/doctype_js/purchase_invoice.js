cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 0 && 1,
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("item_code").get_query = function (doc) {
	return {
		filters: {
			"is_purchase_item": 1,
			"authority": doc.authority
		}
	}
};
erpnext.accounts.PurchaseInvoice = erpnext.accounts.PurchaseInvoice.extend({
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
	scan_barcode: function(){
		let scan_barcode_field = this.frm.fields_dict["scan_barcode"];

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
	},
	
});
$.extend(cur_frm.cscript, new erpnext.accounts.PurchaseInvoice({frm: cur_frm}));

// for backward compatibility: combine new and previous states

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_purchase_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
}
frappe.ui.form.on('Purchase Invoice', {
	refresh: function(frm){
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("ref_pi", "");
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
	onload_post_render: function(frm) {
		frm.page.get_inner_group_button(__("Get items from")).find("button").addClass("hide");
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from && frm.doc.__islocal){
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
	}
});