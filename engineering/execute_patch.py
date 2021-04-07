def execute():
    import frappe
    # Patch Start: Serial No is inactive but in sle it is delivered or in stock
    sr_query = frappe.db.sql("""
        select name,item_code,patch_executed from `tabSerial No`
        where status="Delivered" and item_code = "SL-CPL-302"
        order by creation desc
    """,as_dict=1)

    for idx,sr in enumerate(sr_query):
        print(sr.name)
        print(idx)
        sle_query = frappe.db.sql("""
            select voucher_type,voucher_no,warehouse,company,posting_date,posting_time
            from `tabStock Ledger Entry`
            where item_code = %s and actual_qty > 0 and (serial_no = %s or serial_no like %s or serial_no like %s or serial_no like %s)
            order by timestamp(posting_date,posting_time) desc
            limit 1
        """,(sr.item_code,sr.name, sr.name+'\n%', '%\n'+sr.name, '%\n'+sr.name+'\n%'),as_dict=1)

        doc = frappe.get_doc("Serial No",sr.name)
        if sle_query:
            for sle in sle_query:
                if doc.company != sle.company:
                    doc.db_set('company',sle.company,update_modified=False)
                if doc.warehouse != sle.warehouse:
                    doc.db_set('warehouse',sle.warehouse,update_modified=False)
                if doc.purchase_document_type != sle.voucher_type:
                    doc.db_set('purchase_document_type',sle.voucher_type,update_modified=False)
                if doc.purchase_document_no != sle.voucher_no:
                    doc.db_set('purchase_document_no',sle.voucher_no,update_modified=False)
                if doc.purchase_date != sle.posting_date:
                    doc.db_set('purchase_date',sle.posting_date,update_modified=False)
                if doc.purchase_time != sle.posting_time:
                    doc.db_set('purchase_time',sle.posting_time,update_modified=False)
                if doc.status != "Active":
                    doc.db_set('status',"Active",update_modified=False)


            sle_actual_qty_negative_query = frappe.db.sql("""
                select voucher_type,voucher_no,warehouse,company,posting_date,posting_time
                from `tabStock Ledger Entry`
                FORCE INDEX (company_warehouse_item_index)
                where company = %s and warehouse = %s and item_code = %s and actual_qty < 0 and (serial_no = %s or serial_no like %s or serial_no like %s or serial_no like %s) 
                order by timestamp(posting_date,posting_time) desc
                limit 1
            """,(doc.company,doc.warehouse,sr.item_code,sr.name, sr.name+'\n%', '%\n'+sr.name, '%\n'+sr.name+'\n%'),as_dict=1)

            if sle_actual_qty_negative_query:
                for sle in sle_actual_qty_negative_query:
                    if doc.purchase_date <= sle.posting_date and doc.purchase_time <= sle.posting_time:
                        if doc.delivery_document_type != sle.voucher_type:
                            doc.db_set('delivery_document_type',sle.voucher_type,update_modified=False)
                        if doc.delivery_document_no != sle.voucher_no:
                            doc.db_set('delivery_document_no',sle.voucher_no,update_modified=False)
                        if doc.delivery_date != sle.posting_date:
                            doc.db_set('delivery_date',sle.posting_date,update_modified=False)
                        if doc.delivery_time != sle.posting_time:
                            doc.db_set('delivery_time',sle.posting_time,update_modified=False)
                        if doc.status != "Delivered":
                            doc.db_set('status',"Delivered",update_modified=False)
                        doc.db_set("warehouse",None,update_modified=False)
                    else:
                        doc.db_set('delivery_document_type',None,update_modified=False)
                        doc.db_set('delivery_document_no',None,update_modified=False)
                        doc.db_set('delivery_date',None,update_modified=False)
                        doc.db_set('delivery_time',None,update_modified=False)
            if idx%100 == 0:
                frappe.db.commit()
    # Patch END