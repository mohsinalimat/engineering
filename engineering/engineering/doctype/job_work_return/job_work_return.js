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
			"company": doc.job_work_company
		}
	}
};
cur_frm.fields_dict.s_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.job_work_company
		}
	}
};
cur_frm.fields_dict.jobwork_in_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
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
	on_submit1: function (frm) {
		frappe.run_serially([
			() => {
				if (frm.doc.docstatus == 1 && frm.doc.repack_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
						async: false,
						args: {
							'name': frm.doc.repack_ref
						},
						callback: function (r) {
							if (r.message) {
								frappe.call({
									method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
									async: false,
									args: {
										'name': r.message
									},
									callback: function (r) {
										frappe.msgprint("Submitted");
									}
								});
							}
						}
					});
				}
			},
			() => {
				if (frm.doc.docstatus == 1 && frm.doc.issue_ref) {
					frappe.call({
						method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
						async: false,
						args: {
							'name': frm.doc.issue_ref,
						},
						callback: function (r) {
							if (r.message) {
								frappe.call({
									method: 'engineering.engineering.doc_events.stock_entry.submit_job_work_entry',
									async: false,
									args: {
										'name': r.message
									},
									callback: function (r) {
										frappe.msgprint("Submitted");
									}
								});
							}
						}
					})
				}
			}
		])
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

});
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