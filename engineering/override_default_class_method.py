import frappe
from frappe import _, ValidationError
from frappe.utils import cint, flt, formatdate, format_time
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError
from frappe.model.naming import parse_naming_series
from frappe.permissions import get_doctypes_with_read

@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value):
	# search barcode no
	barcode_data = frappe.db.get_value('Item Barcode', {'barcode': search_value}, ['barcode', 'parent as item_code'], as_dict=True)
	if barcode_data:
		return barcode_data

	# FinByz Changes Srart
	# search package no
	package_no_data = frappe.db.get_value('Item Packing', {'name': search_value, 'docstatus': 1}, ['serial_no as serial_no', 'item_code'], as_dict=True)
	if package_no_data:
		return package_no_data
	# FinByz Changes End

	# search serial no
	serial_no_data = frappe.db.get_value('Serial No', search_value, ['name as serial_no', 'item_code'], as_dict=True)
	if serial_no_data:
		return serial_no_data

	# search batch no
	batch_no_data = frappe.db.get_value('Batch', search_value, ['name as batch_no', 'item as item_code'], as_dict=True)
	if batch_no_data:
		return batch_no_data

	return {}


def get_transactions(self, arg=None):
	doctypes = list(set(frappe.db.sql_list("""select parent
			from `tabDocField` df where fieldname='naming_series'""")
		+ frappe.db.sql_list("""select dt from `tabCustom Field`
			where fieldname='naming_series'""")))

	doctypes = list(set(get_doctypes_with_read()).intersection(set(doctypes)))
	prefixes = ""
	for d in doctypes:
		options = ""
		try:
			options = self.get_options(d)
		except frappe.DoesNotExistError:
			frappe.msgprint(_('Unable to find DocType {0}').format(d))
			#frappe.pass_does_not_exist_error()
			continue

		#finbyz
		if options:
			options = get_naming_series_options(d)
			prefixes = prefixes + "\n" + options
	prefixes.replace("\n\n", "\n")
	prefixes = sorted(list(set(prefixes.split("\n"))))

	custom_prefixes = frappe.get_all('DocType', fields=["autoname"],
		filters={"name": ('not in', doctypes), "autoname":('like', '%.#%'), 'module': ('not in', ['Core'])})
	if custom_prefixes:
		prefixes = prefixes + [d.autoname.rsplit('.', 1)[0] for d in custom_prefixes]

	prefixes = "\n".join(sorted(prefixes))

	return {
		"transactions": "\n".join([''] + sorted(doctypes)),
		"prefixes": prefixes
	}

#finbyz
def get_naming_series_options(doctype):
	meta = frappe.get_meta(doctype)
	options = meta.get_field("naming_series").options.split("\n")	
	options_list = []

	fields = [d.fieldname for d in meta.fields]
	# frappe.msgprint(str(len(options)))

	for option in options:
		parts = option.split('.')

		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		naming_str = parse_naming_series(parts)
		series = {}
		dynamic_field = {}
		field_list = []
		
		for part in parts:
			if part in fields:
				field_list.append(part)
				dynamic_field[part] = (frappe.db.sql_list("select distinct {field} from `tab{doctype}` where {field} is not NULL".format(field=part, doctype=doctype)))
	
		import itertools
		if dynamic_field.items():
			pair = [(k, v) for k, v in dynamic_field.items()]
			key = [item[0] for item in pair]
			value = [item[1] for item in pair]

			combination = list(itertools.product(*value))
			for item in combination:
				name = naming_str
				for k, v in zip(key, item):
					name = name.replace(k, v)

				options_list.append(name)
		
	return "\n".join(options_list)