import frappe
from frappe import _
import json

from frappe.desk.notifications import get_filters_for

def check_sub_string(string, sub_string): 
    """Function to check if string has sub string"""

    return not string.find(sub_string) == -1


def naming_series_name(name, company_series = None):
    """Function to convert naming series name"""
    
    if check_sub_string(name, '.YYYY.'):
        name = name.replace('.YYYY.', '.2020.')
    
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