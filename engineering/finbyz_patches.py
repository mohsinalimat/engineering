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


# Correct Stock Value and diff of Serialized Items

from erpnext.stock.stock_ledger import update_entries_after
import datetime
exceptional_entries = ["MAT-SLE-2020-840287","MAT-SLE-2020-778405"]
sle_diff_query = frappe.db.sql("""
	select sle.name,sle.item_code,sle.warehouse, sle.posting_date, sle.posting_time
	from `tabStock Ledger Entry` as sle
	JOIN `tabCompany` as com on sle.company = com.name
	JOIN `tabStock Entry Detail` as sed on sed.name = sle.voucher_detail_no
	where sle.incoming_rate = 0 and (sle.actual_qty * sle.valuation_rate - sle.stock_value_difference) > 1
	and com.authority = 'Unauthorized' and sle.serial_no IS NOT NULL
""",as_dict=1)
print(len(sle_diff_query))
for sle in sle_diff_query:
	if sle.name not in len_done and sle.name not in exceptional_entries and sle.item_code != "MHP-1273":
		frappe.db.set_value("Stock Ledger Entry",sle.name,"valuation_rate",0)
		print(sle.name)
		new_time = sle.posting_time - datetime.timedelta(minutes=15)
		args = {
			"item_code": sle.item_code,
			"warehouse": sle.warehouse,
			"posting_date": sle.posting_date,
			"posting_time": new_time
		}
		try:
			update_entries_after(args)
			frappe.db.commit()
			len_done.append(sle.name)
		except KeyError:
			exceptional_entries.append(sle.name)




# Correct specific SLE

from erpnext.stock.stock_ledger import update_entries_after
import datetime

sle = frappe.get_doc("Stock Ledger Entry","MAT-SLE-2020-750403")
new_time = sle.posting_time - datetime.timedelta(minutes=15)
args = {
	"item_code": sle.item_code,
	"warehouse": sle.warehouse,
	"posting_date": sle.posting_date,
	"posting_time": new_time
}
update_entries_after(args)



# Patch Start 

from erpnext.stock.stock_ledger import update_entries_after
import datetime
lst =  []

exceptional_entries = []
query = frappe.db.sql("""
	select sle.item_code,sle.warehouse
	from `tabStock Ledger Entry` as sle
	JOIN `tabCompany` as com on sle.company = com.name
	where com.authority = 'Unauthorized' and sle.serial_no IS NOT NULL and sle.posting_date > "2020-08-20"
	and incoming_rate = 0
	group by sle.item_code,sle.warehouse
""",as_dict=1)
print(len(query))   

for sle in query:
	f = open("lexcru_patch.txt", "a")
	if sle not in exceptional_entries and sle not in lst and sle.item_code != "MHP-1273":
		print(sle.item_code + " " + sle.warehouse)
		args = {
			"item_code": sle.item_code,
			"warehouse": sle.warehouse,
			"posting_date": "2020-08-01",
			"posting_time": "00:01:00"
		}
		try:
			update_entries_after(args)
			lst.append(sle)
			f.write(str(sle) + "\n")
			frappe.db.commit()
			f.close()
		except:
			exceptional_entries.append(sle)
			f.write("Exceptional Case" + str(sle) + "\n")
			f.close()

# Patch End



# Patch Start: Find and correct valiation rate diff is more than *5 
lst = []
from erpnext.stock.stock_ledger import update_entries_after
import datetime
query = frappe.db.sql("""
    select sle.name,sle.item_code,sle.warehouse, sle.posting_date, sle.posting_time
    from `tabStock Ledger Entry` as sle
    JOIN `tabCompany` as com on sle.company = com.name
    JOIN `tabStock Entry Detail` as sed on sed.name = sle.voucher_detail_no
    where sed.valuation_rate * 5 <= sle.valuation_rate and sle.voucher_type = 'Stock Entry' and sle.incoming_rate = 0
    and com.authority = 'Unauthorized' and sed.t_warehouse IS NULL and sle.serial_no IS NOT NULL
""",as_dict=1)
for sle in query:
    if sle.name not in lst and sle.name != "MAT-SLE-2020-731372":
        print(sle.name)
        new_time = sle.posting_time - datetime.timedelta(minutes=15)
        args = {
            "item_code": sle.item_code,
            "warehouse": sle.warehouse,
            "posting_date": sle.posting_date,
            "posting_time": new_time
        }
        update_entries_after(args)
        frappe.db.commit()
        lst.append(sle.name)

# Patch End

# Patch Start: replace space in serial_nos in stock ledger entry
sle_query = frappe.db.sql("select name,serial_no from `tabStock Ledger Entry` where serial_no NOT LIKE '' and serial_no LIKE '% %' ",as_dict=1)

for idx,sle in enumerate(sle_query):
	print(sle.name)
	if sle.serial_no.find(" ") != -1:
		print('found')
		serial_no_strip = sle.serial_no.replace(" ","")
		doc = frappe.get_doc("Stock Ledger Entry",sle.name)
		doc.db_set('serial_no',serial_no_strip,update_modified=False)
		if idx%10 == 0:
			frappe.db.commit()

# Patch End