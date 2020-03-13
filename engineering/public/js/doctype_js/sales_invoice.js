frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm){
		frm.page.get_inner_group_button(__("Get items from")).find("button").addClass("hide");
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("ref_si", "");
			frm.set_value("ref_pi", "");
			frm.set_value("inter_company_invoice_reference", "");
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