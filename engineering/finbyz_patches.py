def correct_item_packing():
	from frappe.utils import cstr
	import frappe
	serial_no_list = []
	stock_entry_list = []
	final_serial_no_list = []
	partial_entry = []
	ip_list = frappe.db.sql(f"""
			select
				name, serial_no, warehouse
			from 
				`tabItem Packing`
			where
				work_order IS NOT NULL and stock_entry IS NULL and docstatus = 1
		""", as_dict = True)

	for ip in ip_list:
		sr_dict = {"name":ip.name,"serial_no":ip.serial_no,"warehouse":ip.warehouse}
		serial_no_list.append(sr_dict)

	for packing in serial_no_list:
		stock_entry_list = []
		stock_entry_distint = []
		ip_doc=frappe.get_doc("Item Packing",packing['name'])
		print(packing['name'])
		final_serial_no_list = [s.strip() for s in cstr(packing['serial_no']).strip().upper().replace(',', '\n').split('\n')
			if s.strip()]
		sr_length = len(final_serial_no_list)
		for serial in final_serial_no_list:
			stock_entry,warehouse = frappe.db.get_value("Serial No",serial,['purchase_document_no','warehouse'])
			if stock_entry:
				stock_entry_list.append(stock_entry)
		se_length = len(stock_entry_list)
		if se_length !=0:
			if sr_length == se_length:
				stock_entry_distint = list(set(stock_entry_list))
				if len(stock_entry_distint) == 1:
					print("Pefect")
					ip_doc.db_set("stock_entry",stock_entry_distint[0], update_modified=False)
				else:
					ip_doc.db_set("single_se_not_found",1, update_modified=False)
					ip_doc.db_set("stock_entry",stock_entry_distint[0], update_modified=False)
					print("Multi SE")
			else:
				ip_doc.db_set("partial_entry_not_found",1, update_modified=False)
				ip_doc.db_set("stock_entry",stock_entry_list[0], update_modified=False)
				print("partial SE")
		else:
			ip_doc.db_set("partial_entry_not_found",0, update_modified=False)
			print("se Legth 0")