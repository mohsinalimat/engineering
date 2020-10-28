// cur_frm.fields_dict.items.grid.get_field("item_code").get_query = function(doc,cdt,cdn) {
// 	let d = locals[cdt][cdn];
// 	if(cur_frm.doc.authority == "Authorized"){
// 		return {
// 			filters: {
// 				"item_series": ['NOT IN', [null, '']],
// 			}
// 		}
// 	}else{
// 		return {
// 			filters: {
// 				"item_series": ['IN', [null, '']],
// 			}
// 		}
// 	}
// };


erpnext.stock.DeliveryNoteController = erpnext.stock.DeliveryNoteController.extend({
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
								frappe.model.set_value(item.doctype, item.name, 'serial_no', unique.join('\n'));
								frappe.model.set_value(item.doctype, item.name, 'qty', unique.length);
								flag = true
								frappe.show_alert({message:__("{0} Pcs added for item {1}", [data.no_of_items,data.item_code]), indicator:'green'});
								
							}
						});
						if (flag == false){
							let d =frm.add_child('items');
							frappe.model.set_value(d.doctype, d.name, 'item_code', data.item_code);
							frappe.model.set_value(d.doctype, d.name, 'serial_no', data.serial_no);
							frappe.model.set_value(d.doctype, d.name, 'qty', data.no_of_items);
							frappe.show_alert({message:__("{0} Pcs added for item {1}", [data.no_of_items||1,data.item_code]), indicator:'green'});
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
	
	refresh: function(doc, dt, dn) {
		var me = this;
		// this._super();
		if ((!doc.is_return) && (doc.status!="Closed" || this.frm.is_new())) {
			if (this.frm.doc.docstatus===0) {
				this.frm.add_custom_button(__('Sales Order'),
					function() {
						erpnext.utils.map_current_doc({
							method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
							source_doctype: "Sales Order",
							target: me.frm,
							setters: {
								customer: me.frm.doc.customer || undefined,
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_delivered: ["<", 99.99],
								company: me.frm.doc.company,
								project: me.frm.doc.project || undefined,
							}
						})
					}, __("Get items from"));
			}
		}

		if (!doc.is_return && doc.status!="Closed") {
			if(flt(doc.per_installed, 2) < 100 && doc.docstatus==1)
				this.frm.add_custom_button(__('Installation Note'), function() {
					me.make_installation_note() }, __('Create'));

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Sales Return'), function() {
					me.make_sales_return() }, __('Create'));
			}

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Delivery Trip'), function() {
					me.make_delivery_trip() }, __('Create'));
			}

			if(doc.docstatus==0 && !doc.__islocal) {
				this.frm.add_custom_button(__('Packing Slip'), function() {
					frappe.model.open_mapped_doc({
						method: "erpnext.stock.doctype.delivery_note.delivery_note.make_packing_slip",
						frm: me.frm
					}) }, __('Create'));
			}

			if (!doc.__islocal && doc.docstatus==1) {
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (doc.docstatus==1) {
			this.show_stock_ledger();
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				this.show_general_ledger();
			}
			if (this.frm.has_perm("submit") && doc.status !== "Closed") {
				me.frm.add_custom_button(__("Close"), function() { me.close_delivery_note() },
					__("Status"))
			}
		}

		if(doc.docstatus==1 && !doc.is_return && doc.status!="Closed" && flt(doc.per_billed) < 100) {
			// show Make Invoice button only if Delivery Note is not created from Sales Invoice
			var from_sales_invoice = false;
			from_sales_invoice = me.frm.doc.items.some(function(item) {
				return item.against_sales_invoice ? true : false;
			});

			if(!from_sales_invoice && !doc.final_customer) {
				this.frm.add_custom_button(__('Sales Invoice'), function() {me.make_sales_invoice()}, 
					__('Create'));
				this.frm.add_custom_button(__('Sales Invoice Test'), function() { me.make_sales_invoice_test() },
					__('Create'));
			}
		}

		if(doc.docstatus==1 && doc.status === "Closed" && this.frm.has_perm("submit")) {
			this.frm.add_custom_button(__('Reopen'), function() { me.reopen_delivery_note() },
				__("Status"))
		}
		erpnext.stock.delivery_note.set_print_hide(doc, dt, dn);

		if(doc.docstatus==1 && !doc.is_return && !doc.auto_repeat) {
			cur_frm.add_custom_button(__('Subscription'), function() {
				erpnext.utils.make_subscription(doc.doctype, doc.name)
			}, __('Create'))
		}
	},

    make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "engineering.engineering.doc_events.delivery_note.create_invoice",
			frm: this.frm
		});
	},

	make_sales_invoice_test: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
			frm: this.frm
		});
	}
});
$.extend(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({frm: cur_frm}));

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_sales_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
}
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        if (frm.doc.__islocal){
            frm.trigger('naming_series');
        }
        if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("inter_company_receipt_reference", "");
			frm.set_value("pr_ref", "");
			frm.set_value("dn_ref", "");
		}
    },
    validate:function(frm){
        let item = frm.doc.items;
        $.each(item,(i,row) => {
            if (row.real_qty > row.qty) {
                row.real_qty = row.qty;
            }
        });
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
function removeFromArray(original, remove) {
	return original.filter(value => !remove.includes(value));
} 
frappe.ui.form.on("Delivery Note Item",{
	item_code: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		if(d.qty_per_box){
			d.no_of_boxes = flt(d.qty) / flt(d.qty_per_box)
		}
	},
	qty: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		if(d.qty_per_box){
			d.no_of_boxes = flt(d.qty) / flt(d.qty_per_box)
		}
	}
});