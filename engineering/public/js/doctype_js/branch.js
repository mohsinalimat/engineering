//frappe.require("/assets/engineering/js/override_make_se.js");

frappe.ui.form.on('Branch', {
	setup: (frm) => {
		frm.set_query('comapny', (doc) => {
			return {
				filters: {
					'authority': "Unauthorized"
				}
			}
		});
	}
});