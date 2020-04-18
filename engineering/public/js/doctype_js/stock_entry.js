cur_frm.fields_dict.job_work_company.get_query = function (doc) {
	return {
		filters: {
			"authority": doc.authority,
			"name": ["!=", doc.company]
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