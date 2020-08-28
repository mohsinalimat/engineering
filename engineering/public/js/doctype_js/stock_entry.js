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
this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
	
}

frappe.ui.form.on('Stock Entry', {
	refresh: (frm) => {
		console.log(frm.doc.authority);
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

$.extend(cur_frm.cscript, new erpnext.stock.StockController({ frm: cur_frm }));
