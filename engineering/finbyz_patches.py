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

# Patch Start: Calculate execution time of the function    

def time_fun():
    import time
    import datetime 
    start_time = time.time()
	# function Code
    end_time = time.time()
    return str(datetime.timedelta(seconds = end_time) - (datetime.timedelta(seconds = start_time)))


time_fun()

# Create Index for Complex Queries
# CREATE INDEX active_serial_index ON `tabSerial No` (status,company,warehouse,item_code)
# CREATE INDEX warehouse_item_code_serial_index ON `tabSerial No` (warehouse,item_code,status,purchase_date)
# CREATE INDEX company_warehouse_item_index ON `tabStock Ledger Entry` (company,warehouse,item_code,posting_date)
# CREATE INDEX item_code_index ON `tabSerial No` (item_code)


# Lexcru Slow Query:

# SELECT `current` FROM `tabSeries` WHERE `name`='OSTE-2021F1-' FOR UPDATE\G


# select company, warehouse, status
#                         from `tabSerial No`
#                         where `tabSerial No`.name = 'IFA03176344' and ((((coalesce(`tabSerial No`.`warehouse`, '')='' or `tabSerial No`.`warehouse` in
# 						('Work In Progress - FAC-LWT', 'New Finished Goods - HO-LWT', 'New Work In Progress - FAC-LWT', 'New Work In Progress - SWHTT', 'New Jobwork In - SWHTT', $


# SELECT /*!40001 SQL_NO_CACHE /  FROM `tabSerial No`\G
					
						
# INSERT INTO `tabStock Ledger Entry` (`name`, `owner`, `creation`, `modified`, `modified_by`, `parent
# 	-make_entry in make_sl_entries() in stock_ledger.py and called from stock_entry.py

# Patch Start
sle = frappe.get_doc("Stock Ledger Entry","MAT-SLE-2021-27294")
def get_incoming_value_for_serial_nos(sle):
	from frappe.utils import cint, flt, cstr, now
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
	serial_nos = get_serial_nos(sle.serial_no)
	serial_nos.append("ifa")
	print(sle.voucher_no)
	all_serial_nos = frappe.db.sql(f"""
		select purchase_rate,name,company
		from `tabSerial No`
		where item_code = '{sle.item_code}' and name in (%s)""" % ", ".join(["%s"] * len(serial_nos)),
		tuple(serial_nos), as_dict=1)

	incoming_values = sum([flt(d.purchase_rate) for d in all_serial_nos if d.company==sle.company])

	# Get rate for serial nos which has been transferred to other company
	invalid_serial_nos = [d.name for d in all_serial_nos if d.company!=sle.company]

	invalid_serial_nos += [d.name for d in all_serial_nos if d.company==sle.company and not d.purchase_rate]

	for serial_no in invalid_serial_nos:
		incoming_rate = frappe.db.sql("""
			select incoming_rate
			from `tabStock Ledger Entry`
			FORCE INDEX (company_warehouse_item_index)
			where
				company = %s
				and warehouse = %s
				and item_code = %s
				and actual_qty > 0
				and (serial_no = %s
					or serial_no like %s
					or serial_no like %s
					or serial_no like %s
				)
			order by posting_date desc
			limit 1
		""", (sle.company,sle.warehouse, sle.item_code,serial_no, serial_no+'\n%', '%\n'+serial_no, '%\n'+serial_no+'\n%'))
		print(incoming_rate)
		if not incoming_rate[0][0]:
			frappe.throw("Incoming Rate Not Found For Serial No : {}".format(serial_no))
		incoming_values += flt(incoming_rate[0][0]) if incoming_rate else 0

	return incoming_values
# Patch End

# Patch Start: get incoming_rate of serial no

company = "Factory - Lexcru Water Tech Pvt. Ltd."
warehouse = "Swaminarayan Godown - FAC-LWT"
item_code = "IC-GOS-020"
serial_no = "ifa01472335"

incoming_rate = frappe.db.sql("""
	select incoming_rate
	from `tabStock Ledger Entry`
	FORCE INDEX (company_warehouse_item_index)
	where
		company = %s
		and warehouse = %s
		and item_code = %s
		and actual_qty > 0
		and (serial_no = %s
			or serial_no like %s
			or serial_no like %s
			or serial_no like %s
		)
	order by posting_date desc
	limit 1
""", (company,warehouse, item_code,serial_no, serial_no+'\n%', '%\n'+serial_no, '%\n'+serial_no+'\n%'))

# Patch End