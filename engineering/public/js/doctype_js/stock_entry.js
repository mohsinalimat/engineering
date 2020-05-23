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
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.to_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
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
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
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