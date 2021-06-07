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
	where com.authority = 'Unauthorized' and sle.serial_no IS NULL and sle.posting_date > "2020-08-20"
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
# CREATE INDEX company_item_posting_index ON `tabStock Ledger Entry` (company,item_code,posting_date)
# CREATE INDEX item_posting_creation_index ON `tabStock Ledger Entry` (item_code,posting_date,posting_time,creation)

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

# Patch Start: Serial No is inactive but in sle it is delivered or in stock
		
sr_query = frappe.db.sql("""
	select name,item_code from `tabSerial No`
	where item_code = "PB-DE-252" and status="Delivered" and (warehouse != '' or warehouse IS NOT NULL)
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
				if doc.purchase_date < sle.posting_date:
					set_delivery_values = True
				elif doc.purchase_date == sle.posting_date and doc.purchase_time <= sle.posting_time:
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
		if idx%100 == 0:
			frappe.db.commit()
# Patch END

# Patch Start: in serial_no, if Warehouse is exists but status is not changed

sr_query = frappe.db.sql("""
	select name from `tabSerial No`
	where status="Inactive" and (company != '' or company IS NOT NULL)
	and (warehouse IS NOT NULL and warehouse != '')
	order by creation desc
""",as_dict=1)

list_set_status = []
for idx,sr in enumerate(sr_query):
	fr = open('set_status','r')
	if sr.name not in fr.read():
		fr.close()
		print(sr.name)
		doc = frappe.get_doc("Serial No",sr.name)
		doc.set_status()
		doc.save()
		list_set_status.append((str(sr.name)))
		if idx%30==0:
			frappe.db.commit()
			f = open('set_status','a')
			f.write(str(list_set_status) + "\n")
			f.close()
			list_set_status = []

# Patch END

# Patch Start: set warehouse null where dellivery_document_no is present or status is delivered
frappe.db.sql("""
	update `tabSerial No` as sr
	set sr.warehouse=null where sr.delivery_document_no IS NOT NULL
""")

# Patch End

# Patch Start: update serial no status to delivered where company and package is exists but not warehouse and status inactive

frappe.db.sql("""
	update `tabSerial No`
	set status='Delivered' where (company IS NOT NULL or company != '')
	and (box_serial_no IS NOT NULL or box_serial_no != '')
	and status="Inactive" and (warehouse IS NULL or warehouse = '')
""")

frappe.db.sql("""
	update `tabSerial No`
	set status='Delivered' where (company IS NOT NULL or company != '')
	and status="Inactive" and (warehouse IS NULL or warehouse = '')
""")

frappe.db.sql("""
	select count(name) from `tabSerial No`
	where (company IS NOT NULL or company != '')
	and status="Inactive" and (warehouse IS NULL or warehouse = '')
""")

# Patch End


# Patch Start: update particular serial_no details

serial_no_doc = frappe.get_doc("Serial No","IFA04451932")
serial_no_doc.old_warehouse = serial_no_doc.warehouse
serial_no = serial_no_doc.name
serial_no_doc.update_serial_no_reference(serial_no)
serial_no_doc.save()

# Patch End

# Patch Start: update real_difference_amount and pay_amount_left in purchase and sales invoice
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

# Patch End

frappe.db.sql("""
	update `tabSerial No` set status="Delivered" where (delivery_document_type IS NOT NULL and delivery_document_type!='')
""")

# Changed purchase details and changed status active to inactive of following serial_nos

# IFA04451259 - OSTE-2122SYS1-0004
# IFA04451261 - OSTE-2122SYS1-0004
# IFA04451257
# IFA04451255
# IFA04451254
# IFA04451252
# IFA04451251

# Changed item_code of below listed serials nos as its item code changed from item packing 

['IFA00670694',
'IFA00670695',
'IFA00670696',
'IFA00670697',
'IFA00670698',
'IFA00670699',
'IFA00670700',
'IFA00670701',
'IFA00670702',
'IFA00670703',
'IFA00670704',
'IFA00670705',
'IFA00670706',
'IFA00670707',
'IFA00670708']


sr_no_list = frappe.db.get_value("Stock Entry Detail","9d587cc396","serial_no")
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
serial_nos = get_serial_nos(sr_no_list)

diff_item_code_sr=[]
for sr in serial_nos:
    item_code = frappe.db.get_value("Serial No",sr,'item_code')
    if item_code != "SC-PAA-160":
        diff_item_code_sr.append(sr)

for sr in diff_item_code_sr:
    doc = frappe.get_doc("Serial No","IFA04451261")
    doc.db_set("item_code","SC-CRB-057",update_modified=False)
    doc.db_set("item_name","1 C.T CRUZE CROWN BLACK SYSTEM",update_modified=False)
    doc.db_set("description","CROWN - -",update_modified=False)

lst = ["IFA04451257"
,"IFA04451255"
,"IFA04451254"
,"IFA04451252"
,"IFA04451251"]
for sr in lst:
    doc = frappe.get_doc("Serial No",sr)
    doc.db_set("warehouse",None,update_modified=False)
    doc.db_set("purchase_document_type",None,update_modified=False)
    doc.db_set("purchase_document_no",None,update_modified=False)
    doc.db_set("purchase_rate",0,update_modified=False)
    doc.db_set("purchase_date",None,update_modified=False)
    doc.db_set("purchase_time",None,update_modified=False)
    doc.db_set("status","Inactive",update_modified=False)



sr_no_list = frappe.db.get_value("Stock Entry Detail","c3d6aa20a6","serial_no")
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
serial_nos = get_serial_nos(sr_no_list)

delivery_sr = []
for sr_no in serial_nos:
	status = frappe.db.get_value("Serial No",sr_no,"status")
	if status != "Inactive":
		delivery_sr.append(sr_no)

voucher_no = []
for sr_no in delivery_sr:
	voucher_no.append(frappe.db.get_value("Serial No",sr_no,"delivery_document_no"))



from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
serial_no = frappe.db.get_value("Stock Entry Detail",{"parent":"OSTE-2021F1-9913"},"serial_no")
serial_no_list = get_serial_nos(serial_no)

item_code_changes = []
same_item = []
for sr in serial_no_list:
	if frappe.db.get_value("Serial No",sr,"item_code") != "PL-EC-211":
		item_code_changes.append(sr)
	else:
		same_item.append(sr)

doc = frappe.get_doc("Stock Entry","OSTE-2021F1-9913")
doc.db_set("docstatus",0,update_modified=False)

frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no='OSTE-2021F1-9913'")

from erpnext.stock.stock_ledger import update_entries_after

args = {
	"item_code": "PL-EC-211",
	"warehouse": "New Finished Goods - FAC-LWT",
	"posting_date": "2019-01-01",
	"posting_time": "01:01:00"
}
update_entries_after(args)

from erpnext.stock.stock_ledger import update_entries_after

args = {
	"item_code": "PL-EC-211",
	"warehouse": "New Finished Goods - FAC-LWT",
	"posting_date": "2019-01-01",
	"posting_time": "01:01:00"
}
update_entries_after(args)

frappe.db.commit()


# Patch Start: Create New Serial Nos from Excel File
import xlrd
from engineering.engineering.doctype.serial_no_generator.serial_no_generator import bulk_insert
wb = xlrd.open_workbook('Serial_No_Range DM.xlsx')
sh = wb.sheet_by_name('Query Report')

values = []
user = frappe.session.user
for i in range(1,sh.nrows):
    serial_no = sh.row_values(i)[0]
    qr_code_hash = sh.row_values(i)[1]
    print(sh.row_values(i))

    time = frappe.utils.get_datetime()
    sr_no = ''.join(filter(lambda i: i.isdigit(), serial_no))
    sr_no_info = sr_no[-9:]
    values.append((serial_no, time, time, user, user, serial_no, sr_no_info, qr_code_hash))
    if i%20000 == 0:
        try:
            bulk_insert("Serial No", fields=['name', "creation", "modified", "modified_by", "owner", 'serial_no', 'sr_no_info','qr_code_hash'], values=values)
            frappe.db.commit()
            values =[]
        except Exception as e:
            frappe.db.rollback()
            print(e)

# Patch End



# Patch Start: Change Stock Entry Posting time
frappe.db.sql("update `tabStock Ledger Entry` set posting_time = '20:05:30' where voucher_no='OSTE-2021HO1-1578-1'")

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
serial_no = frappe.db.get_value("Stock Entry Detail",{"parent":"OSTE-2021HO1-1578-1"},"serial_no")
serial_no_list = get_serial_nos(serial_no)
sr_query=[]
for sr in serial_no_list:
    sr_query.append({"name":sr,"item_code":"MDCZ032"})


for idx,sr in enumerate(sr_query):
    print(idx)
    sle_query = frappe.db.sql("""
        select voucher_type,voucher_no,warehouse,company,posting_date,posting_time,creation
        from `tabStock Ledger Entry`
        FORCE INDEX(item_posting_creation_index)
        where item_code = %s and actual_qty > 0 and (serial_no = %s or serial_no like %s or serial_no like %s or serial_no like %s)
        order by posting_date desc, posting_time desc, creation desc
        limit 1
    """,(sr['item_code'],sr['name'], sr['name']+'\n%', '%\n'+sr['name'], '%\n'+sr['name']+'\n%'),as_dict=1)
    doc = frappe.get_doc("Serial No",sr['name'])
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
        """,(doc.company,doc.warehouse,sr['item_code'],sr['name'], sr['name']+'\n%', '%\n'+sr['name'], '%\n'+sr['name']+'\n%'),as_dict=1)

        set_delivery_values = False

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
                    doc.db_set('warehouse',None,update_modified=False)
        if not set_delivery_values:
            doc.db_set('delivery_document_type',None,update_modified=False)
            doc.db_set('delivery_document_no',None,update_modified=False)
            doc.db_set('delivery_date',None,update_modified=False)
            doc.db_set('delivery_time',None,update_modified=False)

    doc.db_set('patch_executed',1,update_modified=False)
    if idx%100 == 0:
        frappe.db.commit()
frappe.db.commit()

# Patch End


frappe.db.sql("""
	update `tabSerial No` as sr
	set sr.purchase_document_type = sle.voucher_type, sr.purchase_document_no = sle.voucher_no, sr.purchase_date = sle.posting_date,
	sr.purchase_time = sle.posting_time, sr.company = sle.company, sr.warehouse = sle.warehouse, sr.status="Active"
	from
	(
		    select item_code,serial_no,voucher_type,voucher_no,posting_date,posting_time,company,warehouse
            from `tabStock Ledger Entry` as sle
			where sle.actual_qty > 0
            order by posting_date desc, posting_time desc, creation desc
            limit 1
	) sle
	where sle.item_code = sr.item_code and (sle.serial_no = sr.name or sle.serial_no like sr.name\n% or serial_no like %\nsr.name or serial_no like  %\nsr.name\n%)
""")