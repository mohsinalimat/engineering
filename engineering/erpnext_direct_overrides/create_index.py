frappe.db.sql("CREATE INDEX company_warehouse_item_index ON `tabStock Ledger Entry` (company,warehouse,item_code,posting_date)")
frappe.db.sql("CREATE INDEX company_w_item_posting_creation_index ON `tabStock Ledger Entry` (company,warehouse,item_code,posting_date,posting_time,creation)")
frappe.db.sql("CREATE INDEX active_serial_index ON `tabSerial No` (status,company,warehouse,item_code)")
frappe.db.sql("CREATE INDEX item_posting_creation_index ON `tabStock Ledger Entry` (item_code,posting_date,posting_time,creation)")
frappe.db.sql("CREATE INDEX company_i_w_pd_pt_c ON `tabStock Ledger Entry` (company,item_code,warehouse,posting_date,posting_time,creation)")
frappe.db.sql("CREATE INDEX sales_invoice_serial ON `tabSerial No` (sales_invoice)")