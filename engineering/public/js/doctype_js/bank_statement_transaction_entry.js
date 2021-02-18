frappe.ui.form.on('Bank Statement Transaction Entry',{
    refresh: function(frm){
        frm.add_custom_button(__("Get Through Company"), function(){
            if (!frm.doc.company){
                frappe.throw("Please Enter Company")
            }
            else if (frm.doc.company){
            frappe.db.get_value("Company",frm.doc.company,'through_company', function(r){
                frm.doc.new_transaction_items.forEach(function (d){
                    frappe.model.set_value(d.doctype, d.name,'through_company',r.through_company)
                })
            })
            }
            frm.refresh_field('new_transaction_items');
            frm.save()
        });
    },
});