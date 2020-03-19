import frappe
from frappe import _
from erpnext.stock.doctype.item.item import get_item_defaults

@frappe.whitelist()
def create_material_request(source_name, target_doc=None):
	doc = frappe.get_doc('Work Order', source_name)

	me = frappe.new_doc("Material Request")
	me.company = doc.company

	me.items = []

	for item in doc.required_items:
		if item.required_qty > item.available_qty_at_source_warehouse:
			item_details = get_item_defaults(item.item_code, doc.company)
			me.append('items', {
				'item_code': item.item_code,
				'qty': item.required_qty - item.available_qty_at_source_warehouse,
				'stock_qty': item.required_qty - item.available_qty_at_source_warehouse,
				'uom': item_details.get('uoms')[0].get('uom'),
				'stock_uom': item_details.get('uoms')[0].get('uom'),
				'description': item.get('description'),
				'conversion_factor': item_details.get('uoms')[0].get('conversion_factor'),
				'warehouse': item.source_warehouse
			})

	return me