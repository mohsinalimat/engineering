erpnext.stock.PurchaseReceiptController = erpnext.stock.PurchaseReceiptController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		if(doc.docstatus===1) {
			this.show_stock_ledger();
			//removed for temporary
			this.show_general_ledger();

			this.frm.add_custom_button(__('Asset'), function() {
				frappe.route_options = {
					purchase_receipt: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset");
			}, __("View"));

			this.frm.add_custom_button(__('Asset Movement'), function() {
				frappe.route_options = {
					reference_name: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset Movement");
			}, __("View"));
		}

		if(!doc.is_return && doc.status!="Closed") {
			if (doc.docstatus == 0) {
				this.frm.add_custom_button(__('Purchase Order'),
					function () {
						erpnext.utils.map_current_doc({
							method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
							source_doctype: "Purchase Order",
							target: me.frm,
							setters: {
								supplier: me.frm.doc.supplier || undefined,
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_received: ["<", 99.99],
								company: me.frm.doc.company
							}
						})
					}, __("Get items from"));
			}

			if(doc.docstatus == 1 && doc.status!="Closed") {
				if (this.frm.has_perm("submit")) {
					cur_frm.add_custom_button(__("Close"), this.close_purchase_receipt, __("Status"))
				}

				cur_frm.add_custom_button(__('Purchase Return'), this.make_purchase_return, __('Create'));

				cur_frm.add_custom_button(__('Make Stock Entry'), cur_frm.cscript['Make Stock Entry'], __('Create'));

				if(flt(doc.per_billed) < 100) {
					this.frm.add_custom_button(__('Purchase Invoice'), function() {me.make_purchase_invoice()}, 
					__('Create'));
					this.frm.add_custom_button(__('Purchase Invoice Test'), function() {me.make_purchase_invoice_test()}, 
					__('Create'));
				}
				cur_frm.add_custom_button(__('Retention Stock Entry'), this.make_retention_stock_entry, __('Create'));

				if(!doc.auto_repeat) {
					cur_frm.add_custom_button(__('Subscription'), function() {
						erpnext.utils.make_subscription(me.frm.doc.doctype, me.frm.doc.name)
					}, __('Create'))
				}

				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}


		if(doc.docstatus==1 && doc.status === "Closed" && this.frm.has_perm("submit")) {
			cur_frm.add_custom_button(__('Reopen'), this.reopen_purchase_receipt, __("Status"))
		}

		this.frm.toggle_reqd("supplier_warehouse", doc.is_subcontracted==="Yes");
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
	
	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "engineering.engineering.doc_events.purchase_receipt.make_purchase_invoice",
			frm: cur_frm
		})
	},

	make_purchase_invoice_test: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
			frm: cur_frm
		})
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
})

$.extend(cur_frm.cscript, new erpnext.stock.PurchaseReceiptController({frm: cur_frm}));

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
frappe.ui.form.on('Purchase Receipt', {
	refresh: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
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
	company: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	}
});
frappe.ui.form.on('Purchase Receipt Item', {
	copy_serial_nos: function(frm,cdt,cdn){
		let d = locals[cdt][cdn]
		let input = $("<textarea>");
		$("body").append(input);
		input.val(d.serial_no).select();

		document.execCommand("copy");
		input.remove();

		frappe.show_alert({
			indicator: 'green',
			message: __('Copied to clipboard.')
		});
		//frappe.utils.copy_to_clipboard(d.item_code)
	}

});
cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 0 && 1,
			"company": doc.company
		}
	}
};