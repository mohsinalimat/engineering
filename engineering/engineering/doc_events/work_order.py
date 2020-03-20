import frappe
from frappe import _
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.stock_ledger import get_previous_sle
from datetime import datetime

@frappe.whitelist()
def create_material_request(source_name, target_doc=None):
	doc = frappe.get_doc('Work Order', source_name)

	me = frappe.new_doc("Material Request")
	me.company = doc.company

	me.items = []

	for item in doc.required_items:
		if (item.required_qty - item.transferred_qty) > item.available_qty_at_source_warehouse:
			item_details = get_item_defaults(item.item_code, doc.company)
			me.append('items', {
				'item_code': item.item_code,
				'qty': (item.required_qty - item.transferred_qty) - item.available_qty_at_source_warehouse,
				'stock_qty': (item.required_qty - item.transferred_qty) - item.available_qty_at_source_warehouse,
				'uom': item_details.get('uoms')[0].get('uom'),
				'stock_uom': item_details.get('uoms')[0].get('uom'),
				'description': item.get('description'),
				'conversion_factor': item_details.get('uoms')[0].get('conversion_factor'),
				'warehouse': item.source_warehouse
			})

	return me

@frappe.whitelist()
def set_actual_qty_in_wo(wo_number):
	wo = frappe.get_doc("Work Order", wo_number)
	for d in wo.get('required_items'):
		previous_sle = get_previous_sle({
			"item_code": d.item_code,
			"warehouse": d.source_warehouse or wo.source_warehouse,
			"posting_date": datetime.now().strftime("%Y-%m-%d"),
			"posting_time": datetime.now().strftime("%H:%M:%S.%f")
		})

		# get actual stock at source warehouse
		d.db_set('available_qty_at_source_warehouse',previous_sle.get("qty_after_transaction") or 0)
		#d.actual_qty = previous_sle.get("qty_after_transaction") or 0
		return "Actual Quantity Updated"