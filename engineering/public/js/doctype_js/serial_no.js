frappe.ui.form.on('Serial No', {
    refresh: function(frm){
        frm.add_custom_button(__("View Stock Ledger Engineering"),function(){
            var today = new Date();
            var dd = today.getDate();
            var mm = today.getMonth()+1;
            var yyyy = today.getFullYear();
            if(dd<10){
                dd='0'+dd;
            } 
            if(mm<10){
                mm='0'+mm;
            } 
            var today = yyyy + '-' + mm + '-' + dd;
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    "doctype": "Fiscal Year",
                    "filters": {"name": "2019-2020"},
                    "fieldname": "year_start_date"
                },
                callback:function(r){
                    console.log(r.message['year_start_date'])
                     window.open(window.location.href.split("#")[0] + "#query-report/Stock Ledger Engineering" + "/?" + "serial_no="+frm.doc.name + "&" +  "item_code="+frm.doc.item_code + "&" + "from_date=" + r.message['year_start_date'] + "&" + "to_date=" + today,"_blank")
                    }
            })
        })
    }
});