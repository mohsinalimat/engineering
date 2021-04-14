def execute():
    import frappe
    # Patch Start: Serial No is inactive but in sle it is delivered or in stock
    sr_query = frappe.db.sql("""
        select name,item_code from `tabSerial No`
        where item_code IS NOT NULL and patch_executed != 1
        order by modified desc
        limit 100000
    """,as_dict=1)

    for idx,sr in enumerate(sr_query):
        print(sr.name)
        print(idx)
        sle_query = frappe.db.sql("""
            select voucher_type,voucher_no,warehouse,company,posting_date,posting_time,creation
            from `tabStock Ledger Entry`
            FORCE INDEX(item_posting_creation_index)
            where item_code = %s and actual_qty > 0 and (serial_no = %s or serial_no like %s or serial_no like %s or serial_no like %s)
            order by posting_date desc, posting_time desc, creation desc
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
                creation_incoming_sle = sle.creation

            sle_actual_qty_negative_query = frappe.db.sql("""
                select voucher_type,voucher_no,warehouse,company,posting_date,posting_time,creation
                from `tabStock Ledger Entry`
                FORCE INDEX (company_w_item_posting_creation_index)
                where company = %s and warehouse = %s and item_code = %s and actual_qty < 0 and (serial_no = %s or serial_no like %s or serial_no like %s or serial_no like %s) 
                order by posting_date desc, posting_time desc, creation desc
                limit 1
            """,(doc.company,doc.warehouse,sr.item_code,sr.name, sr.name+'\n%', '%\n'+sr.name, '%\n'+sr.name+'\n%'),as_dict=1)

            if sle_actual_qty_negative_query:
                for sle in sle_actual_qty_negative_query:
                    if doc.purchase_date < sle.posting_date:
                        set_delivery_values = True
                    elif doc.purchase_date == sle.posting_date and doc.purchase_time < sle.posting_time:
                        set_delivery_values = True
                    elif doc.purchase_date == sle.posting_date and doc.purchase_time == sle.posting_time and creation_incoming_sle < sle.creation:
                        set_delivery_values = True
                    else:
                        set_delivery_values = False
                    
                    if set_delivery_values:
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
        doc.db_set('patch_executed',1,update_modified=False)
        if idx%100 == 0:
            frappe.db.commit()
    frappe.db.commit()
# Patch END




# # Patch Start: Correct Difference between stock balance and item_groupwise_stock_balance report:
# 	#solution: run update_entries_after function where there is difference between stock ledger and bin

# item_warehouse_list = [{'item_code': 'MHP-1273', 'warehouse': 'New Finished Goods - FAC-LWT'},
# {'item_code': 'RPB-3569', 'warehouse': 'Inline Finished - FAC-LWT'},
# {'item_code': 'IL-SLO-048', 'warehouse': 'Jobwork In - SWHTT'}]

# from erpnext.stock.stock_ledger import update_entries_after
# args = {
#     "item_code": "RPB-3569",
#     "warehouse": "Inline Finished - FAC-LWT",
#     "posting_date": "2019-01-01",
#     "posting_time": "01:00:00",
# }
# update_entries_after(args)
# def execute():
#     item_warehouse_list = [{'item_code': 'MCT019', 'warehouse': 'Work In Progress - CWTT'},
#     {'item_code': 'MMS010', 'warehouse': 'Finished Goods - CWTT'},
#     {'item_code': 'MPB005', 'warehouse': 'Work In Progress - CWTT'},
#     {'item_code': 'MRO002', 'warehouse': 'Finished Goods - CWTT'},
#     {'item_code': 'BP-0025W', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'CL-0251', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'CP-0241', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'HC-0064W', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'MR-1151', 'warehouse': 'Inline WIP - FAC-LWT'},
#     {'item_code': 'Pump Accentory Nylon', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RBB-1571', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RBC-1612', 'warehouse': 'Work In Progress - FAC-LWT'},
#     {'item_code': 'RBC-1616', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RBR-1552', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RC-0211', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RCB-1701', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RFC-1651', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RGR-1861', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RLB-1721', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RMC-1741', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RMG-1681', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RPB-3575', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RPT-3136', 'warehouse': 'Inline WIP - FAC-LWT'},
#     {'item_code': 'RPW-1801', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RSC-1959', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RSC-1967', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RSP-2311', 'warehouse': 'New Work In Progress - FAC-LWT'},
#     {'item_code': 'RPG-3455', 'warehouse': 'Work In Progress - LWTIT'}]

#     from erpnext.stock.stock_ledger import update_entries_after
#     for item in item_warehouse_list:
#         print(item)
#         args = {
#             "item_code": item['item_code'],
#             "warehouse": item['warehouse'],
#             "posting_date": "2019-01-01",
#             "posting_time": "01:00:00",
#             "allow_negative_stock":True
#         }
#         update_entries_after(args)

def execute_pi_patch():
    import frappe
    pi_list = frappe.db.sql("select name from `tabPurchase Invoice` WHERE authority = 'Unauthorized' and docstatus=1")

    for idx,pi in enumerate(pi_list):
        print(idx)
        print(pi[0])
        pi_doc = frappe.get_doc("Purchase Invoice", pi[0])

        if pi_doc.authority == "Unauthorized" and not pi_doc.pi_ref:
            for item in pi_doc.items:
                item.db_set('discounted_rate',0,update_modified=False)
                item.db_set('real_qty',0,update_modified=False)

        for item in pi_doc.items:
            item.db_set('discounted_amount',(item.discounted_rate or 0)  * (item.real_qty or 0),update_modified=False)
            item.db_set('discounted_net_amount',item.discounted_amount,update_modified=False)
	
        pi_doc.db_set('discounted_total',sum(x.discounted_amount for x in pi_doc.items),update_modified=False)
        pi_doc.db_set('discounted_net_total',sum(x.discounted_net_amount for x in pi_doc.items),update_modified=False)

        testing_only_tax = 0
        
        for tax in pi_doc.taxes:
            if tax.testing_only:
                testing_only_tax += tax.tax_amount

        pi_doc.db_set('discounted_grand_total',pi_doc.discounted_net_total + pi_doc.total_taxes_and_charges - testing_only_tax,update_modified=False)

        if pi_doc.rounded_total:
            pi_doc.db_set('discounted_rounded_total',round(pi_doc.discounted_grand_total),update_modified=False)
        pi_doc.db_set('real_difference_amount',(pi_doc.rounded_total or pi_doc.grand_total) - (pi_doc.discounted_rounded_total or pi_doc.discounted_grand_total),update_modified=False)
        pi_doc.db_set('pay_amount_left',pi_doc.real_difference_amount,update_modified=False)

        if idx%300 == 0:
            frappe.db.commit()

    frappe.db.commit()

def execute_si_patch():
    import frappe
    si_list = frappe.db.sql("select name from `tabSales Invoice` WHERE authority = 'Unauthorized' and docstatus=1")

    for idx,si in enumerate(si_list):
        print(idx)
        print(si[0])
        si_doc = frappe.get_doc("Sales Invoice", si[0])

        if si_doc.authority == "Unauthorized" and not si_doc.si_ref:
            for item in si_doc.items:
                item.db_set('discounted_rate',0,update_modified=False)
                item.db_set('real_qty',0,update_modified=False)

        for item in si_doc.items:
            item.db_set('discounted_amount',(item.discounted_rate or 0)  * (item.real_qty or 0),update_modified=False)
            item.db_set('discounted_net_amount',item.discounted_amount,update_modified=False)
	
        si_doc.db_set('discounted_total',sum(x.discounted_amount for x in si_doc.items),update_modified=False)
        si_doc.db_set('discounted_net_total',sum(x.discounted_net_amount for x in si_doc.items),update_modified=False)

        testing_only_tax = 0
        
        for tax in si_doc.taxes:
            if tax.testing_only:
                testing_only_tax += tax.tax_amount

        si_doc.db_set('discounted_grand_total',si_doc.discounted_net_total + si_doc.total_taxes_and_charges - testing_only_tax,update_modified=False)

        si_doc.db_set('discounted_rounded_total',round(si_doc.discounted_grand_total),update_modified=False)
        si_doc.db_set('real_difference_amount',(si_doc.rounded_total) - (si_doc.discounted_rounded_total),update_modified=False)
        si_doc.db_set('pay_amount_left',si_doc.real_difference_amount,update_modified=False)

        if idx%300 == 0:
            frappe.db.commit()

    frappe.db.commit()