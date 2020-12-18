// Copyright (c) 2020, FinByz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.material_transfer.get_query = function (doc) {
	return {
		filters: {
			"purpose": 'Material Transfer',
			"stock_entry_type": 'Send to Jobwork',
			"docstatus": 1,
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.item_code.get_query = function (doc) {
	return {
		filters: {
			"is_stock_item": 1
		}
	}
};
cur_frm.fields_dict.company.get_query = function (doc) {
	return {
		filters: {
			"authority": doc.authority
		}
	}
};
cur_frm.fields_dict.job_work_company.get_query = function (doc) {
	return {
		filters: {
			"authority": doc.authority
		}
	}
};

cur_frm.fields_dict.bom_no.get_query = function (doc) {
	return {
		filters: {
			"item": doc.item_code
		}
	}
};
cur_frm.fields_dict.t_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.job_work_company,
			"is_group": ["!=", 1]
		}
	}
};
cur_frm.fields_dict.s_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.job_work_company,
			"is_group": ["!=", 1]
		}
	}
};
cur_frm.fields_dict.jobwork_in_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group": ["!=", 1]
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.additional_cost.grid.get_field("expense_account").get_query = function (doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	return {
		filters: {
			"company": doc.company
		}
	}
};
this.frm.cscript.onload = function (frm) { 
	this.frm.set_query("batch_no", function (doc) {
		if (!doc.item_code) {
			frappe.msgprint(__("Please select Item"));
		} else {
			return {
				query: "engineering.query.get_batch_no",
				filters: {
					'item_code': doc.item_code,
					'warehouse': doc.jobwork_in_warehouse
				}
			}
		}
	});
}
frappe.ui.form.on('Job Work Return', {
	
	refresh: function(frm){
		if (frm.doc.docstatus == 1 && frm.doc.issue_ref && !frm.doc.repack_ref){
			frm.add_custom_button("Make JOB Work Manufacturing Entry", function() {
				setTimeout(() => {
					frm.remove_custom_button('Make JOB Work Manufacturing Entry');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.job_work_return.job_work_return.enqueue_job_work_manufacturing_button",
					args:
					{
						'name': frm.doc.name
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
		if (frm.doc.docstatus == 1 && !frm.doc.issue_ref && frm.doc.repack_ref){
			frm.add_custom_button("Make JOB Work Finish Entry", function() {
				setTimeout(() => {
					frm.remove_custom_button('Make JOB Work Finish Entry');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.job_work_return.job_work_return.enqueue_send_jobwork_finish_entry_button",
					args:
					{
						'name': frm.doc.name
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
		if (frm.doc.docstatus == 1 && !frm.doc.issue_ref && !frm.doc.repack_ref){
			frm.add_custom_button("Make JOB Work Finish Entry", function() {
				setTimeout(() => {
					frm.remove_custom_button('Make JOB Work Finish Entry');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.job_work_return.job_work_return.enqueue_send_jobwork_finish_entry_button",
					args:
					{
						'name': frm.doc.name
					},
					freeze: true,
					callback: function(r){
						if (r.message){
							frappe.msgprint(r.message);
						}
					}
				})
			})
			frm.add_custom_button("Make JOB Work Manufacturing Entry", function() {
				setTimeout(() => {
					frm.remove_custom_button('Make JOB Work Manufacturing Entry');
					}, 3);
				frappe.call({
					method: "engineering.engineering.doctype.job_work_return.job_work_return.enqueue_job_work_manufacturing_button",
					args:
					{
						'name': frm.doc.name
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
	},
	validate: function (frm, cdt, cdn) {
		frm.trigger('set_basic_rate')
		frm.trigger('set_default_account')
		
		// $.each(me.frm.doc.items || [], function (i, d) {
		
		// 	if (d.item_code) {
		// 		var args = {
		// 			'item_code': d.item_code,
		// 			'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
		// 			'transfer_qty': d.transfer_qty,
		// 			'serial_no': d.serial_no,
		// 			'bom_no': d.bom_no,
		// 			'expense_account': d.expense_account,
		// 			'cost_center': d.cost_center,
		// 			'company': frm.doc.company,
		// 			'qty': d.qty,
		// 			'voucher_type': frm.doc.doctype,
		// 			'voucher_no': d.name,
		// 			'allow_zero_valuation': 1,
		// 		};

		// 		return frappe.call({
		// 			doc: frm.doc,
		// 			method: "get_item_details",
		// 			args: args,
		// 			callback: function (r) {
		// 				if (r.message) {
		// 					console.log(r.message)
		// 					$.each(r.message, function (k, v) {
		// 						frappe.model.set_value(d.doctype,d.name,k,v)
		// 						d[k] = v;
		// 					});
		// 					frm.events.calculate_amount(frm);
		// 					refresh_field("items");
		// 				}
		// 			}
		// 		});
		// 	}
		// });
	},
	bom_no: function (frm) {
		frm.set_value("qty", "");
		frm.doc.items = [];
		refresh_field('items');
	},
	qty: function (frm) {
		frm.doc.items = [];
		refresh_field('items');
		if (frm.doc.bom_no != "") {
			frappe.model.with_doc("BOM", frm.doc.bom_no, function () {
				var os_doc = frappe.model.get_doc("BOM", frm.doc.bom_no);

				$.each(os_doc.items, function (index, row) {
					let d = frm.add_child("items");

					d.item_code = row.item_code;
					d.item_name = row.item_name;
					d.uom = row.uom;
					d.basic_rate = row.rate;
					d.qty = flt(flt(frm.doc.qty * row.qty) / os_doc.quantity);
					d.amount = d.basic_rate * d.qty;
				});
				frm.refresh_field('items');
			});
			
		}
	},
	calculate_basic_amount: function (frm, item) {
		item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
			precision("basic_amount", item));

		frm.events.calculate_amount(frm);
	},

	calculate_amount: function (frm) {
		frm.events.calculate_total_additional_costs(frm);

		const total_basic_amount = frappe.utils.sum(
			(frm.doc.items || []).map(function (i) { return i.t_warehouse ? flt(i.basic_amount) : 0; })
		);

		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (item.t_warehouse && total_basic_amount) {
				item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost),
				precision("amount", item));

			item.valuation_rate = flt(flt(item.basic_rate)
				+ (flt(item.additional_cost) / flt(item.transfer_qty)),
				precision("valuation_rate", item));
		}

		refresh_field('items');
	},

	calculate_total_additional_costs: function (frm) {
		const total_additional_costs = frappe.utils.sum(
			(frm.doc.additional_costs || []).map(function (c) { return flt(c.amount); })
		);

		frm.set_value("total_additional_costs",
			flt(total_additional_costs, precision("total_additional_costs")));
	},
	set_basic_rate: function (frm, cdt, cdn) {
		const item = locals[cdt][cdn];
		item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

		const args = {
			'item_code': item.item_code,
			'posting_date': frm.doc.posting_date,
			'posting_time': frm.doc.posting_time,
			'warehouse': cstr(item.s_warehouse) || cstr(item.t_warehouse),
			'serial_no': item.serial_no,
			'company': frm.doc.company,
			'qty': item.s_warehouse ? -1 * flt(item.transfer_qty) : flt(item.transfer_qty),
			'voucher_type': frm.doc.doctype,
			'voucher_no': item.name,
			'allow_zero_valuation': 1,
		};

		if (item.item_code || item.serial_no) {
			frappe.call({
				method: "erpnext.stock.utils.get_incoming_rate",
				args: {
					args: args
				},
				callback: function (r) {
					frappe.model.set_value(cdt, cdn, 'basic_rate', (r.message || 0.0));
					frm.events.calculate_basic_amount(frm, item);
				}
			});
		}
	},
	set_default_account: function (frm) {
		frappe.db.get_value("Company", frm.doc.company, 'cost_center', function (r) {
			if (r.cost_center) { 
				$.each(me.frm.doc.items || [], function (i, d) {
					frappe.model.set_value(d.doctype, d.name, 'cost_center', r.cost_center)
				});
			}
		})
		if (frm.doc.company && erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			return frm.call({
				method: "erpnext.accounts.utils.get_company_default",
				args: {
					"fieldname": "stock_adjustment_account",
					"company": frm.doc.company
				},
				callback: function (r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function (i, d) {
							frappe.model.set_value(d.doctype, d.name,'expense_account',r.message)
						});
					}
				}
			});
		}
	},
	add_serial_no: function(frm){
		select_batch_and_serial_no(frm)
	},
	scan_barcode: function(frm){
		let scan_barcode_field = cur_frm.fields_dict["scan_barcode"];

		let show_description = function(idx, exist = null) {
			if (exist) {
				scan_barcode_field.set_new_description(__('Row #{0}: Qty increased by 1', [idx]));
			} else {
				scan_barcode_field.set_new_description(__('Row #{0}: Item added', [idx]));
			}
		};

	
		
		if(frm.doc.scan_barcode) {
			frappe.call({
				method: "engineering.override_default_class_method.search_serial_or_batch_or_barcode_number",
				args: { search_value: frm.doc.scan_barcode },
				callback: function(r){
					 
					if (r.message.item_code){
						let data = r.message;
						var flag = false;
						(frm.doc.items || []).forEach(function(item, idx) {
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
frappe.ui.form.on('Job Work Return Item', {
	
	uom: function (doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.uom && d.item_code) {
			return frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details",
				args: {
					item_code: d.item_code,
					uom: d.uom,
					qty: d.qty
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, r.message);
					}
				}
			});
		}
	},
	item_code: function (frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.item_code) {
			var args = {
				'item_code': d.item_code,
				'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
				'transfer_qty': d.transfer_qty,
				'serial_no': d.serial_no,
				'bom_no': d.bom_no,
				'expense_account': d.expense_account,
				'cost_center': d.cost_center,
				'company': frm.doc.company,
				'qty': d.qty,
				'voucher_type': frm.doc.doctype,
				'voucher_no': d.name,
				'allow_zero_valuation': 1,
			};

			return frappe.call({
				doc: frm.doc,
				method: "get_item_details",
				args: args,
				callback: function (r) {
					if (r.message) {
						var d = locals[cdt][cdn];
						$.each(r.message, function (k, v) {
							d[k] = v;
						});
						frm.events.calculate_amount(frm);
						refresh_field("items");
					}
				}
			});
		}
	},
	expense_account: function (frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "expense_account");
	},
	cost_center: function (frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	},
	qty: function (frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},
	conversion_factor: function (frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},
})

const select_batch_and_serial_no = (frm) => {
	frappe.require("assets/engineering/js/serial_no_batch_selector.js", function() {
		new erpnext.SerialNoBatchSelector({
			frm: frm
		});
	});
}