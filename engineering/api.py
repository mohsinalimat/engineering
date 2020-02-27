import frappe
from frappe import _
import json

from frappe.desk.notifications import get_filters_for
from frappe.model.mapper import get_mapped_doc

from frappe.utils import getdate

def check_sub_string(string, sub_string): 
	"""Function to check if string has sub string"""

	return not string.find(sub_string) == -1


def naming_series_name(name, company_series = None):
	"""Function to convert naming series name"""

	from erpnext.accounts.utils import get_fiscal_year
	
	if check_sub_string(name, '.YYYY.'):
		name = name.replace('.YYYY.', '2020')
	
	# changing value of fiscal according to current fiscal year 
	if check_sub_string(name, '.fiscal.'):
		current_fiscal = frappe.db.get_value('Global Defaults', None, 'current_fiscal_year')
		fiscal = frappe.db.get_value("Fiscal Year", str(current_fiscal),'fiscal')
		name = name.replace('.fiscal.', str(fiscal))

	# changing value of company series according to company
	if company_series:
		if check_sub_string(name, 'company_series.'):
			name = name.replace('company_series.', str(company_series))
		elif check_sub_string(name, '.company_series.'):
			name = name.replace('.company_series.', str(company_series))

	# removing the hash symbol from naming series
	if check_sub_string(name, ".#"):
		name = name.replace('#', '')
		if name[-1] == '.':
			name = name[:-1]
	
	return name


# all whitelist functions bellow

@frappe.whitelist()
def check_counter_series(name, company_series = None):
	"""Function to get series value for naming series"""

	# renaming the name for naming series
	name = naming_series_name(name, company_series)

	# Checking the current series value
	check = frappe.db.get_value('Series', name, 'current', order_by="name")
	
	# returning the incremented value of check for series value
	if check == 0:
		return 1
	elif check == None:
		# if no current value is found for naming series inserting that naming series with current value 0
		frappe.db.sql("insert into tabSeries (name, current) values ('{}', 0)".format(name))
		return 1
	else:
		return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1

@frappe.whitelist()
def before_naming(self, method = None):
	"""Function for naming the name of naming series"""

	# if from is not ammended and series_value is greater than zero then 
	if not self.amended_from:
		if self.series_value:
			
			if self.series_value > 0:
				
				# renaming the name for naming series
				name = naming_series_name(self.naming_series, self.company_series)
				
				# Checking the current series value
				check = frappe.db.get_value('Series', name, 'current', order_by="name")
				frappe.msgprint(str(check))
				# if no current value is found inserting 0 for current value for this naming series
				if check == 0:
					pass
				elif not check:
					frappe.db.sql("insert into tabSeries (name, current) values ('{}', 0)".format(name))
				
				# Updating the naming series decremented by 1 for current naming series
				frappe.db.sql("update `tabSeries` set current = {} where name = '{}'".format(int(self.series_value) - 1, name))

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
		fieldname = links.get("non_standard_fieldnames", {}).get(d, links.fieldname)
		data = {"name": d}
		if filters:
			# get the fieldname for the current document
			# we only need open documents related to the current document
			filters[fieldname] = name
			total = len(frappe.get_list(d, fields="name",
				filters=filters, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
			data["open_count"] = total

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
			],
		}

	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def restrict_access():
	role_permission_list = frappe.get_all("User Permission", filters = {
		"allow": "Authority", "for_value": "Unauthorized"
	}, fields = ['name', 'system_genrated'])
	for item in role_permission_list:
		if not item['system_genrated']:
			doc = get_mapped_doc("User Permission", item['name'], {
				"User Permission": {
					"doctype": "Backup User Permission",
				}
			}, ignore_permissions = True)

			doc.save(ignore_permissions = True)
		
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)
	
	user_list = frappe.get_all("User", filters = {'enabled': 1}, fields = ['email', 'username'])
	for user in user_list:
		if user['username'] != 'administrator' and user['email'] != 'guest@example.com':
			doc = frappe.new_doc("User Permission")

			doc.user = user['email']
			doc.allow = 'Authority'
			doc.for_value = 'Authorized'
			doc.apply_to_all_doctypes = 1
			doc.system_genrated = 1

			try:
				doc.save(ignore_permissions = True)
			except:
				pass
	frappe.set_value("Global Defaults", "Global Defaults", "restricted_access", 1)
	frappe.db.commit()
	frappe.msgprint("Restricted Access")

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

		doc.save()
		
		frappe.delete_doc("Backup User Permission", item['name'], ignore_permissions = True)
	
	user_permission_list = frappe.get_all("User Permission", filters = {'system_genrated': 1})

	for item in user_permission_list:
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)

	frappe.set_value("Global Defaults", "Global Defaults", "restricted_access", 0)
	frappe.db.commit()

	frappe.msgprint("All Permission Reversed")
