# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, cint, getdate, now, date_diff
from erpnext.stock.utils import add_additional_uom_columns
from erpnext.stock.report.stock_ledger.stock_ledger import get_item_group_condition

from erpnext.stock.report.stock_ageing.stock_ageing import get_fifo_queue, get_average_age

from six import iteritems
import collections

def execute(filters=None):
	#validate_filters(filters)

	if not filters: filters = {}


	from_date = filters.get('from_date')
	to_date = filters.get('to_date')

	if filters.get("company"):
		company_currency = erpnext.get_company_currency(filters.get("company"))
	else:
		company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	if filters.get('show_stock_ageing_data'):
		filters['show_warehouse_wise_stock'] = True
		item_wise_fifo_queue = get_fifo_queue(filters, sle)

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	if filters.get('show_reorder_details'):
		item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	data, new_data = [], []
	item_company, conversion_factors = {}, {}

	_func = lambda x: x[1]

	for (company, item, warehouse) in sorted(iwb_map):
		if item_map.get(item):
			qty_dict = iwb_map[(company, item, warehouse)]
			item_reorder_level = 0
			item_reorder_qty = 0
			if filters.get('show_reorder_details'):
				if item + warehouse in item_reorder_detail_map:
					item_reorder_level = item_reorder_detail_map[item + warehouse]["warehouse_reorder_level"]
					item_reorder_qty = item_reorder_detail_map[item + warehouse]["warehouse_reorder_qty"]

			report_data = {
				'currency': company_currency,
				'item_code': item,
				'warehouse': warehouse,
				'company': company,
				'reorder_level': item_reorder_level,
				'reorder_qty': item_reorder_qty,
			}
			report_data.update(item_map[item])
			report_data.update(qty_dict)

			if include_uom:
				conversion_factors.setdefault(item, item_map[item].conversion_factor)

			if filters.get('show_stock_ageing_data'):
				fifo_queue = item_wise_fifo_queue[(item, warehouse)].get('fifo_queue')

				stock_ageing_data = {
					'average_age': 0,
					'earliest_age': 0,
					'latest_age': 0
				}
				if fifo_queue:
					fifo_queue = sorted(filter(_func, fifo_queue), key=_func)
					if not fifo_queue: continue

					stock_ageing_data['average_age'] = get_average_age(fifo_queue, to_date)
					stock_ageing_data['earliest_age'] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data['latest_age'] = date_diff(to_date, fifo_queue[-1][1])

				report_data.update(stock_ageing_data)
			item_code = report_data['item_code']
			company = report_data['company']
			warehouse = report_data['warehouse']
			report_data['stock_ledger'] = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
				target="_blank" item_code='{item_code}' company='{company}' warehouse='{warehouse if filters.get('show_warehouse_wise_balance') else ''}' from_date='{from_date}' to_date='{to_date}'
				onClick=view_stock_leder_report(this.getAttribute('item_code'),this.getAttribute('company'),this.getAttribute('warehouse'),this.getAttribute('from_date'),this.getAttribute('to_date'))>View Stock Ledger</button>"""
				
			if not filters.get('show_warehouse_wise_balance'):
				key = (report_data['company'],report_data['item_code'])
				if key not in item_company:
					item_company[key] = report_data
					new_data.append(item_company[key])
				else:
					for k,v in item_company[key].items():
						if (isinstance(v, float) or isinstance(v, int)):
							if(k=='opening_rate') and item_company[key]['opening_qty']:
								item_company[key].update({k:flt(item_company[key]['opening_val'])/flt(item_company[key]['opening_qty'])})
							elif(k=='in_rate') and item_company[key]['in_qty']:
								item_company[key].update({k:flt(item_company[key]['in_val'])/flt(item_company[key]['in_qty'])})
							elif(k=='out_rate') and item_company[key]['out_qty']:
								item_company[key].update({k:flt(item_company[key]['out_val'])/flt(item_company[key]['out_qty'])})
							elif(k=='bal_rate') and item_company[key]['bal_qty']:
								item_company[key].update({k:flt(item_company[key]['bal_val'])/flt(item_company[key]['bal_qty'])})
							else:
								item_company[key].update({k:flt(v)+flt(report_data[k])})
			else:
				data.append(report_data)
	data = new_data if new_data else data

	add_additional_uom_columns(columns, data, include_uom, conversion_factors)
	# for row in data:
	# 	item_code = row['item_code']
	# 	company = row['company']
	# 	warehouse = row['warehouse']
	# 	row['stock_ledger'] = f"""<button style='margin-left:5px;border:none;color: #fff; background-color: #5e64ff; padding: 3px 5px;border-radius: 5px;'
	# 		target="_blank" item_code='{item_code}' company='{company}' warehouse='{warehouse}' from_date='{from_date}' to_date='{to_date}'
	# 		onClick=view_stock_leder_report(this.getAttribute('item_code'),this.getAttribute('company'),this.getAttribute('warehouse'),this.getAttribute('from_date'),this.getAttribute('to_date'))>View Stock Ledger</button>"""
		
	# 	if not filters.get('show_warehouse_wise_balance'):
	# 		key = (row['company'],row['item_code'])
	# 		if key not in item_company:
	# 			item_company[key] = row
	# 			new_data.append(item_company[key])
	# 		else:
	# 			for k,v in item_company[key].items():
	# 				if v and (isinstance(v, float) or isinstance(v, int)):
	# 					if(k=='opening_rate'):
	# 						item_company[key].update({k:flt(item_company[key]['opening_val'])/flt(item_company[key]['opening_qty'])})
	# 					elif(k=='in_rate'):
	# 						item_company[key].update({k:flt(item_company[key]['in_val'])/flt(item_company[key]['in_qty'])})
	# 					elif(k=='out_rate'):
	# 						item_company[key].update({k:flt(item_company[key]['out_val'])/flt(item_company[key]['out_qty'])})
	# 					elif(k=='bal_rate'):
	# 						item_company[key].update({k:flt(item_company[key]['bal_val'])/flt(item_company[key]['bal_qty'])})
	# 					else:
	# 						item_company[key].update({k:flt(v)+flt(row[k])})
	return columns, data

def get_columns(filters):
	"""return columns"""
	columns = [
		{"label": _("Item Name"), "fieldname": "item_name", "width": 200},
		{"label": _("Opening Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
	]
	if filters.get('show_rate_value'):
		columns +=[
			{"label": _("Opening Rate"), "fieldname": "opening_rate", "fieldtype": "Float", "width": 80},
			{"label": _("Opening Value"), "fieldname": "opening_val", "fieldtype": "Currency", "width": 110, "options": "currency"},
		]
	columns+=[
			{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
	]
	if filters.get('show_rate_value'):
		columns +=[
			{"label": _("In Rate"), "fieldname": "in_rate", "fieldtype": "Float", "width": 80},
			{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Float", "width": 80},
		]
	columns +=[
			{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
	]
	if filters.get('show_rate_value'):
		columns +=[
			{"label": _("Out Rate"), "fieldname": "out_rate", "fieldtype": "Float", "width": 80},
			{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Float", "width": 80},
		]
	columns +=[
			{"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
	]
	if filters.get('show_rate_value'):
		columns +=[
			{"label": _("Balance Rate"), "fieldname": "bal_rate", "fieldtype": "Float", "width": 80},
			{"label": _("Balance Value"), "fieldname": "bal_val", "fieldtype": "Currency", "width": 100, "options": "currency"},
		]
	if filters.get('show_reorder_details'):
		columns +=[
			{"label": _("Reorder Level"), "fieldname": "reorder_level", "fieldtype": "Float", "width": 80, "convertible": "qty"},
			{"label": _("Reorder Qty"), "fieldname": "reorder_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		]
	columns +=[
			{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
			{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
			{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90}]

	if filters.get('show_warehouse_wise_balance'):
		columns	+= [{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130}]

	columns +=[{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130},
			{"label": _("Stock Ledger"), "fieldname": "stock_ledger", "fieldtype": "button", "width": 120}
		]

	if filters.get('show_stock_ageing_data'):
		columns += [{'label': _('Average Age'), 'fieldname': 'average_age', 'width': 100},
		{'label': _('Earliest Age'), 'fieldname': 'earliest_age', 'width': 100},
		{'label': _('Latest Age'), 'fieldname': 'latest_age', 'width': 100}]

	if filters.get('show_variant_attributes'):
		columns += [{'label': att_name, 'fieldname': att_name, 'width': 100} for att_name in get_variants_attributes()]

	return columns

def get_conditions(filters):
	conditions = ""
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date"):
		conditions += " and sle.posting_date <= %s" % frappe.db.escape(filters.get("to_date"))
	else:
		frappe.throw(_("'To Date' is required"))

	if filters.get("company"):
		conditions += " and sle.company = %s" % frappe.db.escape(filters.get("company"))
	else:
		company_list = frappe.db.get_list("Company",{'authority':"Unauthorized"})
		data = ', '.join(f"'{i.name}'" for i in company_list)
		conditions += " and sle.company in (%s)" % data

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value("Warehouse",
			filters.get("warehouse"), ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions += " and exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and sle.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt)

	if filters.get("warehouse_type") and not filters.get("warehouse"):
		conditions += " and exists (select name from `tabWarehouse` wh \
			where wh.warehouse_type = '%s' and sle.warehouse = wh.name)"%(filters.get("warehouse_type"))

	return conditions

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = ' and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i, percent=False) for i in items]))

	conditions = get_conditions(filters)

	return frappe.db.sql("""
		select
			sle.item_code, sle.warehouse, sle.posting_date, sle.actual_qty, sle.valuation_rate,
			sle.company, sle.voucher_type, sle.qty_after_transaction, sle.stock_value_difference,
			sle.item_code as name, sle.voucher_no, IFNULL(se.stock_entry_type,'') as stock_entry_type
		from
			`tabStock Ledger Entry` sle 
			force index (posting_sort_index)
			LEFT JOIN `tabStock Entry` as se on se.name = sle.voucher_no

		where sle.docstatus < 2 %s %s
		order by sle.posting_date, sle.posting_time, sle.creation, sle.actual_qty""" % #nosec
		(item_conditions_sql, conditions), as_dict=1)

def get_item_warehouse_map(filters, sle):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	for d in sle:
		key = (d.company, d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict({
				"opening_qty": 0.0, "opening_val": 0.0, "opening_rate":0.0,
				"in_qty": 0.0, "in_val": 0.0, "in_rate":0.0,
				"out_qty": 0.0, "out_val": 0.0, "out_rate":0.0,
				"bal_qty": 0.0, "bal_val": 0.0, "bal_rate": 0.0,
				"val_rate": 0.0
			})

		qty_dict = iwb_map[(d.company, d.item_code, d.warehouse)]

		if d.voucher_type == "Stock Reconciliation":
			qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date:
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff
			if qty_dict.opening_val and qty_dict.opening_qty:
				qty_dict.opening_rate = flt(qty_dict.opening_val) / flt(qty_dict.opening_qty)
			else:
				qty_dict.opening_rate = 0.0

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(qty_diff, float_precision) >= 0:
				if not filters.get('show_internal_transfers') and d.stock_entry_type in ["Material Transfer","Material Transfer for Manufacture","Material Transfer for Manufacturing"]:
					qty_dict.in_qty += 0
					qty_dict.in_val += 0
				else:
					qty_dict.in_qty += qty_diff
					qty_dict.in_val += value_diff					
				if qty_dict.in_val and qty_dict.in_qty:
					qty_dict.in_rate = flt(qty_dict.in_val) / flt(qty_dict.in_qty)
				else:
					qty_dict.in_rate = 0.0
			else:
				if not filters.get('show_internal_transfers') and d.stock_entry_type in ["Material Transfer","Material Transfer for Manufacture","Material Transfer for Manufacturing"]:
					qty_dict.out_qty += 0
					qty_dict.out_val += 0
				else:
					qty_dict.out_qty += abs(qty_diff)
					qty_dict.out_val += abs(value_diff)					
				if qty_dict.out_val and qty_dict.out_qty:
					qty_dict.out_rate = flt(qty_dict.out_val) / flt(qty_dict.out_qty)
				else:
					qty_dict.out_rate = 0.0

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff
		if qty_dict.bal_val and qty_dict.bal_qty:
			qty_dict.bal_rate = flt(qty_dict.bal_val) / flt(qty_dict.bal_qty)
		else:
			qty_dict.bal_rate = 0.0
	if not filters.get('show_0_qty_inventory'):
		iwb_map = filter_items_with_no_transactions(iwb_map, float_precision)

	return iwb_map

def filter_items_with_no_transactions(iwb_map, float_precision):
	for (company, item, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(company, item, warehouse)]
			
		no_transactions = True
		for key, val in iteritems(qty_dict):
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			iwb_map.pop((company, item, warehouse))

	return iwb_map

def get_items(filters):
	conditions = []
	conditions.append("ifnull(disabled,0) = 0")
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sle, filters):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sle]))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if filters.get("include_uom"):
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(filters.get("include_uom"))

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom %s
		from
			`tabItem` item
			%s
		where
			item.name in (%s)
	""" % (cf_field, cf_join, ','.join(['%s'] *len(items))), items, as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	if filters.get('show_variant_attributes', 0) == 1:
		variant_values = get_variant_values_for(list(item_details))
		item_details = {k: v.update(variant_values.get(k, {})) for k, v in iteritems(item_details)}

	return item_details

def get_item_reorder_details(items):
	item_reorder_details = frappe._dict()

	if items:
		item_reorder_details = frappe.db.sql("""
			select parent, warehouse, warehouse_reorder_qty, warehouse_reorder_level
			from `tabItem Reorder`
			where parent in ({0})
		""".format(', '.join([frappe.db.escape(i, percent=False) for i in items])), as_dict=1)

	return dict((d.parent + d.warehouse, d) for d in item_reorder_details)

@frappe.whitelist()
def validate_filters(filters):
	if not (filters.get("company") or filters.get("warehouse") or filters.get("item_code")):
		frappe.throw(_("Please set filter based on Item or Warehouse or Company due to a large amount of entries."))


	# if not (filters.get("company") or filters.get("warehouse") or filters.get("item_code")):
	# 	sle_count = flt(frappe.db.sql("""select count(name) from `tabStock Ledger Entry`""")[0][0])
	# 	if sle_count > 500000:	
	# 			frappe.throw(_("Please set filter based on Item or Warehouse or Company due to a large amount of entries."))

def get_variants_attributes():
	'''Return all item variant attributes.'''
	return [i.name for i in frappe.get_all('Item Attribute')]

def get_variant_values_for(items):
	'''Returns variant values for items.'''
	attribute_map = {}
	for attr in frappe.db.sql('''select parent, attribute, attribute_value
		from `tabItem Variant Attribute` where parent in (%s)
		''' % ", ".join(["%s"] * len(items)), tuple(items), as_dict=1):
			attribute_map.setdefault(attr['parent'], {})
			attribute_map[attr['parent']].update({attr['attribute']: attr['attribute_value']})

	return attribute_map