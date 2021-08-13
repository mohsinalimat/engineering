frappe.ui.form.on("BOM", {
    refresh: function(frm) {
        frm.remove_custom_button("Update Cost");
        frm.add_custom_button(__("Update BOM Cost"), function() {
            frm.trigger('update_bom_cost')
        });
    },
    before_save: function(frm){
        frm.trigger('calculate_additional_cost')
    },
    update_bom_cost: function (frm) {
        return frappe.call({
            method: "engineering.engineering.doc_events.bom.update_bom_cost",
            freeze: true,
            args: {
                doc: frm.doc.name,
                update_parent: true,
                from_child_bom: false,
                save: frm.doc.docstatus === 1 ? true : false
            },
            callback: function (r) {
                refresh_field("items");
                frm.refresh_fields();
                frm.reload_doc()
                
            }
        });
    },
    calculate_additional_cost: function(frm){
        var sum_additional_cost = 0
        frm.doc.additional_cost.forEach(function(d){
            sum_additional_cost += flt(d.amount)
        });
        frm.set_value('additional_amount',flt(sum_additional_cost))
    }
})

frappe.ui.form.on("BOM Additional Cost", {
	rate: function(frm, cdt, cdn){
		let d = locals[cdt][cdn]
		frappe.model.set_value(d.doctype,d.name,'amount',flt(flt(d.qty) * flt(d.rate)))
        frm.events.calculate_additional_cost(frm);
    },
})