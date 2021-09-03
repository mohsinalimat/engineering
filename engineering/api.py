import frappe
from frappe import _
import json
from datetime import date
import datetime

from frappe.desk.notifications import get_filters_for
from frappe.model.mapper import get_mapped_doc

from frappe.utils import getdate, flt
from erpnext.accounts.utils import get_fiscal_year


def check_sub_string(string, sub_string): 
	"""Function to check if string has sub string"""

	return not string.find(sub_string) == -1


def naming_series_name(name, fiscal, company_series=None):
	if company_series:
		name = name.replace('company_series', str(company_series))
	
	name = name.replace('YYYY', str(datetime.date.today().year))
	name = name.replace('YY', str(datetime.date.today().year)[2:])
	name = name.replace('MM', f'{datetime.date.today().month:02d}')
	name = name.replace('DD', f'{datetime.date.today().day:02d}')
	name = name.replace('fiscal', str(fiscal))
	name = name.replace('#', '')
	name = name.replace('.', '')
	
	return name


# all whitelist functions bellow
@frappe.whitelist()
def get_fiscal(date):
	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	return fiscal if fiscal else fy.split("-")[0][2:] + fy.split("-")[1][2:]

@frappe.whitelist()
def check_counter_series(name, company_series = None, date = None):
	
	if not date:
		date = datetime.date.today()
	
	
	fiscal = get_fiscal(date)
	
	name = naming_series_name(name, fiscal, company_series)
	
	check = frappe.db.get_value('Series', name, 'current', order_by="name")
	
	if check == 0:
		return 1
	elif check == None:
		frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
		return 1
	else:
		return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1

@frappe.whitelist()
def before_naming(self, method):
	if not self.amended_from:
		
		date = self.get("transaction_date") or self.get("posting_date") or getdate()
		fiscal = get_fiscal(date)
		self.fiscal = fiscal

		if self.get('series_value'):
			if self.series_value > 0:
				name = naming_series_name(self.naming_series, fiscal,self.company_series)
				
				check = frappe.db.get_value('Series', name, 'current', order_by="name")
				if check == 0:
					pass
				elif not check:
					frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
				
				frappe.db.sql(f"update `tabSeries` set current = {int(self.series_value) - 1} where name = '{name}'")
		
@frappe.whitelist()
def docs_before_naming(self, method = None):
	from erpnext.accounts.utils import get_fiscal_year

	date = self.get("transaction_date") or self.get("posting_date") or getdate()

	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	if fiscal:
		self.fiscal = fiscal
	else:
		fy_years = fy.split("-")
		fiscal = fy_years[0][2:] + "-" + fy_years[1][2:]
		self.fiscal = fiscal


@frappe.whitelist()
@frappe.read_only()
def get_open_count(doctype, name, items=[]):
	'''Get open count for given transactions and filters

	:param doctype: Reference DocType
	:param name: Reference Name
	:param transactions: List of transactions (json/dict)
	:param filters: optional filters (json/list)'''

	if frappe.flags.in_migrate or frappe.flags.in_install:
		return {
			"count": []
		}

	frappe.has_permission(doc=frappe.get_doc(doctype, name), throw=True)

	meta = frappe.get_meta(doctype)
	links = meta.get_dashboard_data()

	# compile all items in a list
	if not items:
		for group in links.transactions:
			items.extend(group.get("items"))

	if not isinstance(items, list):
		items = json.loads(items)

	out = []
	for d in items:
		if d in links.get("internal_links", {}):
			# internal link
			continue

		filters = get_filters_for(d)
		fieldname = links.get("non_standard_fieldnames", {}).get(d, links.get('fieldname'))
		data = {"name": d}
		if filters:
			# get the fieldname for the current document
			# we only need open documents related to the current document
			filters[fieldname] = name
			# Finbyz Changes Start: frappe.get_all replaced with frappe.get_list
			total = len(frappe.get_list(d, fields="name",
				filters=filters, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
			data["open_count"] = total
		# Finbyz Changes Start: frappe.get_all replaced with frappe.get_list
		total = len(frappe.get_list(d, fields="name",
			filters={fieldname: name}, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
		data["count"] = total
		out.append(data)

	out = {
		"count": out,
	}

	module = frappe.get_meta_module(doctype)
	if hasattr(module, "get_timeline_data"):
		out["timeline_data"] = module.get_timeline_data(doctype, name)

	return out

def get_inter_company_details(doc, doctype):
	party = None
	company = None

	if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"]:
		party = frappe.db.get_value("Supplier", {"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Customer", doc.customer, "represents_company")
	elif doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		party = frappe.db.get_value("Customer", {"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

	return {
		"party": party,
		"company": company
	}

def validate_inter_company_transaction(doc, doctype):
	price_list = None
	details = get_inter_company_details(doc, doctype)

	if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"]:
		price_list = doc.selling_price_list
	elif doctype in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
		price_list = doc.buying_price_list
	
	if price_list:
		valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	else:
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))
	
	if not valid_price_list:
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))
	
	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Delivery Note", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))
	
	company = details.get("company")
	if company:
		default_currency = frappe.get_cached_value('Company', company, "default_currency")
		if default_currency != doc.currency:
			frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))
	else:
		frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))
	
	return

def make_inter_company_transaction(self, doctype, target_doctype, link_field, target_doc=None, field_map={}, child_field_map={}):
	source_doc  = frappe.get_doc(doctype, self.name)

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		if self.amended_from:
			name = frappe.db.get_value(target_doctype, {link_field: self.amended_from}, "name")
			target.amended_from = name
		
		if source.taxes_and_charges:
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")
			
			target.taxes_and_charges = source.taxes_and_charges.replace(
				source_company_abbr, target_company_abbr
			)
			
			# if not target.taxes:
			target.taxes = source.taxes
			
			for index, item in enumerate(source.taxes):
				target.taxes[index].account_head = item.account_head.replace(
					source_company_abbr, target_company_abbr
				)

		target.run_method("set_missing_values")


	def update_details(source_doc, target_doc, source_parent):
		if target_doc.doctype in ["Purchase Invoice", "Purchase Receipt", "Purchase Order"]:
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
		elif target_doc.doctype in ["Sales Invoice", "Delivery Note", "Sales Order"]:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list
		else:
			frappe.throw(_("Invalid Request!"))
		
	def update_items(source_doc, target_doc, source_parent):
		target_company_abbr = frappe.db.get_value("Company", source_parent.supplier, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
		if source_parent.doctype == "Purchase Order":
			target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
	
	doclist = get_mapped_doc(doctype, self.name,	{
		doctype: {
			"doctype": target_doctype,
			"postprocess": update_details,
			"field_map": field_map,
			"field_no_map": [
				"taxes_and_charges",
				"series_value",
			],
		},
		doctype +" Item": {
			"doctype": target_doctype + " Item",
			"field_map": child_field_map,
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse"
			], "postprocess": update_items
		}

	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def restrict_access():
	unauthorized_companies_all = frappe.get_all("Company",{'authority':'Unauthorized'})
	unauthorized_companies = [row.name for row in unauthorized_companies_all]
	role_permission_list = frappe.get_all("User Permission", filters = {
		"allow": "Authority", "for_value": "Unauthorized"
	}, fields = ['name', 'system_genrated'], ignore_permissions = True)

	unauthorized_companies_permission_list = frappe.get_all("User Permission", filters = {
		"allow": "Company", "for_value":('IN',unauthorized_companies)
	}, fields = ['name', 'system_genrated'], ignore_permissions = True)
	final_list = role_permission_list + unauthorized_companies_permission_list

	report_list=[]
	data = frappe.get_all("Testing Report Detail",filters={'parent':'Testing Report'},fields=['report'])
	for d in data:
		report_list.append(d['report'])
	if report_list:
		for report in report_list:
			if frappe.db.exists("Custom Role",{'report': report}):
				doc = get_mapped_doc("Custom Role", {'report': report}, {
					"Custom Role": {
						"doctype": "Backup Custom Role",
					}
				}, ignore_permissions = True)

				try:
					doc.save(ignore_permissions = True)
				except:
					pass
				doc_name = frappe.get_all("Custom Role",{'report': report})
				frappe.delete_doc("Custom Role", doc_name[0].name, ignore_permissions = True)

	for item in final_list:
		if not item['system_genrated']:
			doc = get_mapped_doc("User Permission", item['name'], {
				"User Permission": {
					"doctype": "Backup User Permission",
				}
			}, ignore_permissions = True)

			try:
				doc.save(ignore_permissions = True)
			except:
				pass
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)
	
	user_list = frappe.get_all("User", filters = {'enabled': 1}, fields = ['name', 'username'], ignore_permissions = True)
	for user in user_list:
		if user['username'] != 'administrator' and user['name'] != 'guest@example.com':
			
			if not frappe.db.exists({
				'doctype': 'User Permission',
				'user': user['name'],
				'allow': 'Authority',
				'for_value': 'Authorized',
				'apply_to_all_doctypes': 1
			}):
				doc = frappe.new_doc("User Permission")

				doc.user = user['name']
				doc.allow = 'Authority'
				doc.for_value = 'Authorized'
				doc.apply_to_all_doctypes = 1
				doc.system_genrated = 1

				try:
					doc.save(ignore_permissions = True)
				except:
					pass
	frappe.db.set_value("Global Defaults", "Global Defaults", "restricted_access", 1)
	frappe.db.commit()
	# frappe.msgprint("Restricted Access")
	return "success"

@frappe.whitelist()
def reverse_restrict_access():
	permission_list = frappe.get_all("Backup User Permission")
	for item in permission_list:
		print(item['name'])
		doc = get_mapped_doc("Backup User Permission", item['name'], {
			"Backup User Permission": {
				"doctype": "User Permission",
			}
		})

		doc.save(ignore_permissions = True)
		
		frappe.delete_doc("Backup User Permission", item['name'], ignore_permissions = True)

	report_permission_list = frappe.get_all("Backup Custom Role")
	for row in report_permission_list:
		doc = get_mapped_doc("Backup Custom Role", row['name'], {
			"Backup Custom Role": {
				"doctype": "Custom Role",
			}
		})

		doc.save(ignore_permissions = True)
		
		frappe.delete_doc("Backup Custom Role", row['name'], ignore_permissions = True)

	
	user_permission_list = frappe.get_all("User Permission", filters = {'system_genrated': 1})

	for item in user_permission_list:
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)

	frappe.set_value("Global Defaults", "Global Defaults", "restricted_access", 0)
	frappe.db.commit()

	frappe.msgprint("All Permission Reversed")

@frappe.whitelist()
def get_serial_no_series(name, posting_date):
	current_fiscal = get_fiscal_year(posting_date)[0]
	
	return str(name) + str(frappe.db.get_value("Fiscal Year", current_fiscal, 'fiscal_series'))

@frappe.whitelist()
def create_credit_note(company,customer_code,item_detail=None):
	if company and customer_code:
		doc = frappe.new_doc("Sales Invoice")
		doc.company = company
		doc.customer = customer_code
		doc.naming_series = 'CR-.fiscal.company_series.-.####'
		doc.posting_date = datetime.date.today()
		doc.posting_time = datetime.datetime.now().strftime ("%H:%M:%S")
		doc.is_return = 1
		doc.created_by_api = 1
		doc.selling_price_list = frappe.db.get_value("Customer",customer_code,'default_price_list') or frappe.db.get_single_value('Selling Settings', 'selling_price_list')
		# item_detail =json.load(item_detail)
		for item in item_detail.get('item_detail'):
			item_series = frappe.db.get_value('Item',item['item_code'],'item_series')
			if not item_series:
				frappe.throw(_('Item Series is mandatory for item {0}').format(item['item_code']))
			rate = frappe.db.get_value("Item Price",{'item_code':item_series,'price_list':doc.selling_price_list},'price_list_rate')
			doc.append('items',{
				'item_variant': item['item_code'],
				'item_code': item_series,
				'qty': -(item['qty']),
				'rate': rate or 0,
				'conversion_factor': 1
			})
		doc.save(ignore_permissions = True)
		if doc.taxes_and_charges:
			tax_doc = frappe.get_doc('Sales Taxes and Charges Template',doc.taxes_and_charges)
			for row in tax_doc.taxes:
				doc.append('taxes',{
					'charge_type': row.charge_type,
					'row_id': row.row_id,
					'account_head': row.account_head,
					'description': row.description,
					'included_in_print_rate': row.included_in_print_rate,
					'cost_center': row.cost_center,
					'rate': row.rate,
					'tax_amount': row.tax_amount
				})
		doc.run_method("set_missing_values")
		doc.run_method('calculate_taxes_and_totals')
		doc.save(ignore_permissions = True)
		doc.submit()
		return doc.name , abs(doc.rounded_total)

@frappe.whitelist()
def get_delivery_detail(delivery_note):
	if delivery_note:
		item_list = []
		doc = frappe.get_doc("Delivery Note",delivery_note)
		for row in doc.items:
			if row.item_packing:
				item_list.append({'item_code':row.item_code,'item_name':row.item_name,'item_group':frappe.db.escape(row.item_group),"qty_per_box":row.qty_per_box,"item_packing":row.item_packing,"technician_points":frappe.db.get_value("Item",row.item_code,'technician_points'),"dealer_points":frappe.db.get_value("Item",row.item_code,'dealer_points'),"reward_points":frappe.db.get_value("Item",row.item_code,'reward_points'),"retailer_points":frappe.db.get_value("Item",row.item_code,'retailer_points'),"brand":frappe.db.get_value("Item",row.item_code,'brand')})
		return item_list

@frappe.whitelist()
def get_item_packing_detail(item_packing):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
	if item_packing:
		data = []
		doc = frappe.get_doc("Item Packing",item_packing)
		serial_nos =  get_serial_nos(doc.serial_no)
		dispatch_date = frappe.db.get_value("Serial No",serial_nos[0],'delivery_date')
		data.append({'name':doc.name,'retailer_points': doc.retailer_points,'dealer_points': doc.dealer_points,'dispatch_date': dispatch_date})
		return data

def update_discounted_amount(self):
	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0.0) * (item.real_qty or 0.0)
		item.discounted_net_amount = item.discounted_amount

		try:
			item.discounted_net_rate = item.discounted_net_amount / item.real_qty
		except:
			item.discounted_net_rate = 0.0

# def update_so_date_based_on_po():
# 	data = frappe.get_list("Purchase Order", fields = ['name', 'transaction_date','inter_company_order_reference'])

# 	for i in data:
# 		if i.inter_company_order_reference:
# 			print(i.inter_company_order_reference)
# 			frappe.db.set_value("Sales Order", i.inter_company_order_reference, 'transaction_date', i.transaction_date, update_modified = False)
	
# 	frappe.db.commit()


# Multiprocessing Start

import frappe.database.mariadb.database
import os, time
from multiprocessing import Pool
pool = None

def init():
	global pool
	print("PID %d: initializing pool..." % os.getpid())
	pool = frappe.db

def do_work(q):
	# con = pool.get_connection()
	# print("PID %d: using connection %s" % (os.getpid(), con))
	# c = con.cursor()
	print(frappe.db.get_list('DefaultValue',{"name":"0ed848240e"}))
	# c.execute(q)
	# res = c.fetchall()
	# con.close()
	time.sleep(5)

def main():
	p = Pool(2,initializer=init)
	for res in p.map(do_work,['a','b','c','d','e']):
		print(res)
	p.close()
	p.join()

def call_main():
	main()

# Multiprocessing End