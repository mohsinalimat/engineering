frappe.db.sql("CREATE INDEX company_warehouse_item_index ON `tabStock Ledger Entry` (company,warehouse,item_code,posting_date)")
frappe.db.sql("CREATE INDEX company_w_item_posting_creation_index ON `tabStock Ledger Entry` (company,warehouse,item_code,posting_date,posting_time,creation)")
frappe.db.sql("CREATE INDEX active_serial_index ON `tabSerial No` (status,company,warehouse,item_code)")