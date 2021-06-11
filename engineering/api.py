import frappe
from frappe import _
import json
from datetime import date
import datetime

from frappe.desk.notifications import get_filters_for
from frappe.model.mapper import get_mapped_doc

from frappe.utils import getdate, flt
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.get_item_details import get_price_list_rate


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

def get_rm_rate(self, arg):
	"""	Get raw material rate as per selected method, if bom exists takes bom cost """
	rate = 0
	if not self.rm_cost_as_per:
		self.rm_cost_as_per = "Valuation Rate"

	if arg.get('scrap_items'):
		rate = get_valuation_rate(arg)
	elif arg:
		#Customer Provided parts will have zero rate
		if not frappe.db.get_value('Item', arg["item_code"], 'is_customer_provided_item'):
			if arg.get('bom_no') and self.set_rate_of_sub_assembly_item_based_on_bom:
				rate = flt(get_bom_unitcost(self,arg['bom_no'])) * (arg.get("conversion_factor") or 1)
			else:
				if self.rm_cost_as_per == 'Valuation Rate':
					rate = get_valuation_rate(self,arg) * (arg.get("conversion_factor") or 1)
				elif self.rm_cost_as_per == 'Last Purchase Rate':
					rate = get_company_wise_rate(self,arg) * (arg.get("conversion_factor") or 1)
				elif self.rm_cost_as_per == "Price List":
					if not self.buying_price_list:
						frappe.throw(_("Please select Price List"))
					args = frappe._dict({
						"doctype": "BOM",
						"price_list": self.buying_price_list,
						"qty": arg.get("qty") or 1,
						"uom": arg.get("uom") or arg.get("stock_uom"),
						"stock_uom": arg.get("stock_uom"),
						"transaction_type": "buying",
						"company": self.company,
						"currency": self.currency,
						"conversion_rate": 1, # Passed conversion rate as 1 purposefully, as conversion rate is applied at the end of the function
						"conversion_factor": arg.get("conversion_factor") or 1,
						"plc_conversion_rate": 1,
						"ignore_party": True
					})
					item_doc = frappe.get_doc("Item", arg.get("item_code"))
					out = frappe._dict()
					get_price_list_rate(args, item_doc, out)
					rate = out.price_list_rate

				if not rate:
					if self.rm_cost_as_per == "Price List":
						frappe.msgprint(_("Price not found for item {0} in price list {1}")
							.format(arg["item_code"], self.buying_price_list), alert=True)
					else:
						frappe.msgprint(_("{0} not found for item {1}")
							.format(self.rm_cost_as_per, arg["item_code"]), alert=True)

	return flt(rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1)

def get_company_wise_rate(self,arg):
	rate = flt(arg.get('last_purchase_rate'))
		# or frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")) \
		# 	* (arg.get("conversion_factor") or 1)
		# Finbyz Changes: Replaced above line with below query because of get rate from company filter
	if not rate:
		purchase_rate_query = frappe.db.sql("""
			select incoming_rate
			from `tabStock Ledger Entry`
			where item_code = '{}' and incoming_rate > 0 and voucher_type in ('Purchase Receipt','Purchase Invoice') and company = '{}'
			order by timestamp(posting_date, posting_time) desc
			limit 1
		""".format(arg['item_code'],arg.get('company') or self.company))
		if purchase_rate_query:
			rate = purchase_rate_query[0][0]
		else:
			rate = frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")
	return rate

def get_valuation_rate(self, args):
	""" Get weighted average of valuation rate from all warehouses """

	total_qty, total_value, valuation_rate = 0.0, 0.0, 0.0
	for d in frappe.db.sql("""select b.actual_qty, b.stock_value from `tabBin` as b
		JOIN `tabWarehouse` as w on w.name = b.warehouse
		where b.item_code=%s and w.company = '{}'""".format(self.company), args['item_code'], as_dict=1):
			total_qty += flt(d.actual_qty)
			total_value += flt(d.stock_value)

	if total_qty:
		valuation_rate =  total_value / total_qty

	if valuation_rate <= 0:
		last_valuation_rate = frappe.db.sql("""select valuation_rate
			from `tabStock Ledger Entry`
			where item_code = %s and valuation_rate > 0 and company = '{}'
			order by posting_date desc, posting_time desc, creation desc limit 1""".format(self.company), args['item_code'])

		valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

	if not valuation_rate:
		valuation_rate = frappe.db.get_value("Item", args['item_code'], "valuation_rate")

	return flt(valuation_rate)


def get_bom_unitcost(self, bom_no):
	bom = frappe.db.sql("""select name, base_total_cost/quantity as unit_cost from `tabBOM`
		where is_active = 1 and name = %s and company = '{}'""".format(self.company), bom_no, as_dict=1)
	return bom and bom[0]['unit_cost'] or 0