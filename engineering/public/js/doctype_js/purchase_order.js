cur_frm.fields_dict.items.grid.get_field("item_code").get_query = function (doc) {
	return {
		filters: {
			"is_purchase_item": 1,
			"authority": doc.authority
		}
	}
};
erpnext.buying.PurchaseOrderController = erpnext.buying.PurchaseOrderController.extend({
	calculate_taxes: function() {
		var me = this;
		this.frm.doc.rounding_adjustment = 0;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(this.frm.doc["items"] || [], function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			$.each(me.frm.doc["taxes"] || [], function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);

				// Adjust divisional loss to the last item
				if (tax.charge_type == "Actual") {
					actual_tax_dict[tax.idx] -= current_tax_amount;
					if (n == me.frm.doc["items"].length - 1) {
						current_tax_amount += actual_tax_dict[tax.idx];
					}
				}

				// accumulate tax amount into tax.tax_amount
				if (tax.charge_type != "Actual" &&
					!(me.discount_amount_applied && me.frm.doc.apply_discount_on=="Grand Total")) {
					tax.tax_amount += current_tax_amount;
				}

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// tax amount after discount amount
				tax.tax_amount_after_discount_amount += current_tax_amount;

				// for buying
				if(tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = (tax.category == "Valuation") ? 0.0 : current_tax_amount;

					current_tax_amount *= (tax.add_deduct_tax == "Deduct") ? -1.0 : 1.0;
				}

				// note: grand_total_for_current_item contains the contribution of
				// item's amount, previously applied tax and the current tax on that item
				if(i==0) {
					tax.grand_total_for_current_item = flt(item.discounted_net_amount + current_tax_amount);
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.doc["taxes"][i-1].grand_total_for_current_item + current_tax_amount);
				}

				// set precision in the last item iteration
				if (n == me.frm.doc["items"].length - 1) {
					me.round_off_totals(tax);

					// in tax.total, accumulate grand total for each item
					me.set_cumulative_total(i, tax);

					me.set_in_company_currency(tax,
						["total", "tax_amount", "tax_amount_after_discount_amount"]);

					// adjust Discount Amount loss in last tax iteration
					if ((i == me.frm.doc["taxes"].length - 1) && me.discount_amount_applied
						&& me.frm.doc.apply_discount_on == "Grand Total" && me.frm.doc.discount_amount) {
						me.frm.doc.rounding_adjustment = flt(me.frm.doc.grand_total -
							flt(me.frm.doc.discount_amount) - tax.total, precision("rounding_adjustment"));
					}
				}
			});
		});
	},
	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.net_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount;
		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		this.set_item_wise_tax(item, tax, tax_rate, current_tax_amount);

		return current_tax_amount;
	},
// added
	
	
});

cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 0 && 1,
			"company": doc.company
		}
	}
};
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

frappe.ui.form.on('Purchase Order', {
	refresh: function(frm){
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("so_ref", null);
			frm.set_value("inter_company_order_reference", null);
		}
		if (frm.doc.__islocal){
			if (cur_frm.doc.company){
				frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
					frm.set_value('company_series', r.company_series);
				});
			}
			frm.trigger('company');
		}
	},
	
	select_billing_address: function(frm) {
		// var me = this;
		if(frm.doc.select_billing_address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {"address_dict": frm.doc.select_billing_address },
				callback: function(r) {
					if(r.message) {
						frm.set_value("billing_address", r.message)
					}
				}
			})
		} else {
			frm.set_value("billing_address", "");
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
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		frm.trigger('update_price_list');
	},
	supplier: function(frm){
		frm.trigger('update_price_list');
	},
	update_price_list: function(frm){
		if (frm.doc.company && frm.doc.supplier){
			frappe.call({
				method: 'engineering.engineering.doc_events.purchase_order.get_price_list',
				args: {
					"company": frm.doc.company,
					"party": frm.doc.supplier
				},
				callback: function(r){
					frm.set_value('buying_price_list', r.message)
				}
			})
		}
	}
});

frappe.ui.form.on('Purchase Order Item', {
	last_5_transaction: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		frappe.call({
			method: "engineering.engineering.doc_events.purchase_order.get_last_5_transaction_details",
			args: {
				name:d.name,
				item_code: d.item_code,
				supplier: frm.doc.supplier
			},
			callback: function (r) {
				frappe.msgprint({
					message: r.message,
					title: "Item Code : " + d.item_code + " And Supplier : " + frm.doc.supplier,
					wide: true,
				});
			}
		})
	}
});