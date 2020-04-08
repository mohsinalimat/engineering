import frappe
from frappe import _, ValidationError
from frappe.utils import cint, flt, formatdate, format_time
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError

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