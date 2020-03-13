frappe.ui.form.on('Delivery Note', {
    onload: function(frm) {
        if (frm.doc.__islocal){
            frm.trigger('naming_series');
        }
        if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("inter_company_receipt_reference", "");
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
        if (frm.doc.company && !frm.doc.amended_from){
            console.log(1)
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
    on_submit: function(frm){
        frm.trigger('onload_post_render')
    },
    onload_post_render: function(frm){
        frm.trigger('si_menu_hide');
    },
    si_menu_hide: function(frm){
        
        let $group = cur_frm.page.get_inner_group_button("Create");
                
        let li_length = $group.find("ul li");
        for (let i = 0; i < li_length.length -1; i++) {		
            var li = $group.find(".dropdown-menu").children("li")[i];
            if (li.getElementsByTagName("a")[0].innerHTML == "Sales Invoice")
                $group.find(".dropdown-menu").children("li")[i].remove();
        }
        
        if (!frm.doc.__islocal && frm.doc.docstatus == 1 && frm.doc.status != 'Cancelled') {
            frm.add_custom_button(__("Sales Invoice"), function () {
                frappe.model.open_mapped_doc({
                    method: "engineering.engineering.doc_events.delivery_note.create_invoice",
                    frm: cur_frm
                })
            },
            __("Create"));
            frm.add_custom_button(__("Sales Invoice Test"), function () {
                frappe.model.open_mapped_doc({
                    method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
                    frm: cur_frm
                })
            },
            __("Create"));
            frm.add_custom_button(__("Inter Company Purchase Receipt"), function () {
                frappe.model.open_mapped_doc({
                    method: "engineering.engineering.doc_events.delivery_note.make_inter_company_purchase_receipt",
                    frm: cur_frm
                })
            },
            __("Create"));
        }
    },
    refresh: function(doc) {
        if (doc.docstatus == 1 && !doc.inter_company_receipt_reference) {
            frappe.model.with_doc("Customer", me.frm.doc.customer, function() {
                // var customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
                // var internal = customer.is_internal_customer;
                // var disabled = customer.disabled;
                if (internal == 1 && disabled == 0) {
                    me.frm.add_custom_button("Inter Company Receipt", function() {
                        this.make_inter_company_receipt();
                    }, __('Create'));
                }
            });
        }
    },
    make_inter_company_receipt: function() {
        frappe.model.open_mapped_doc({
            method: "engineering.doc_events.delivery_note.make_inter_company_purchase_receipt",
            frm: me.frm
        });
    },
    on_submit: function(frm){
		if (frm.doc.docstatus == 1 && frm.doc.inter_company_receipt_reference){
			frappe.call({
				method: 'engineering.engineering.doc_events.delivery_note.submit_purchase_receipt',
				args: {
					'pr_number': frm.doc.inter_company_receipt_reference
				},
				callback: function(r){
                    if (r.message) {
					    
                    }
                }
			})
		}
	}
});