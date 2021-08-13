# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import functools
from past.builtins import cmp
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	item_group = get_item_group(filters)

	if not item_group:
		return None
	
	item_group = filter_item_group(filters, item_group)

	out = prepare_data(filters, item_group)
	data = get_final_out(filters, out)

	return data	

def get_item_group(filters):
	item_group = frappe.db.sql("""
		select 
			name, parent_item_group, 1 as is_group
		from
			`tabItem Group`
		order by lft""", as_dict=True)

	bom_item = frappe.db.sql("""
		select
			bom.name as bom_name, bom.item as name, bom.item as item_code ,bom.item_name, bom.raw_material_cost, bom.rmc_valuation_amount, bom.rmc_last_purchase_amount,
			bom.total_operational_cost, bom.total_cost, bom.total_valuation_cost, bom.total_last_purchase_cost,
			item.item_group as parent_item_group, 0 as is_group
		from
			`tabBOM` as bom
			JOIN `tabItem` as item on item.name = bom.item
		where
			bom.is_default = 1 and bom.company = '{}' and bom.docstatus = 1
	""".format(filters.get('company')), as_dict = True)
	item_map = {}
	if filters.get('price_list'):
		item_map = get_price_list_item_map(filters)
	for data in bom_item:
		data.price_list_rate = item_map.get(data.name) or 0

		if filters.get('rm_cost_based_on') == "Valuation Rate":
			data.raw_material_cost = flt(data.rmc_valuation_amount,2)
			data.total_cost = flt(data.total_valuation_cost,2)
		elif filters.get('rm_cost_based_on') == "Last Purchase Rate":
			data.raw_material_cost = flt(data.rmc_last_purchase_amount,2)
			data.total_cost = flt(data.total_last_purchase_cost,2)

		if data.price_list_rate:
			value_diff = abs(flt(data.price_list_rate,2)- flt(data.total_cost,2))
			data.margin = flt(abs((flt(value_diff) / flt(data.total_cost,2)) * 100),2)
	return (item_group + bom_item)

				
def get_price_list_item_map(filters):
	data = frappe.db.sql("""
		select
			item_code as name,price_list_rate
		from 
			`tabItem Price`
		where
			price_list = '{}'
	""".format(filters.get('price_list')), as_dict = True)

	item_map = {}

	for row in data:
		item_map[row.name] = row.price_list_rate
		
	return item_map

def filter_item_group(filters,item_group, depth=10):
	parent_children_map = {}
	item_group_by_name = {}
	
	for d in item_group:
		item_group_by_name[d.name] = d
		parent_children_map.setdefault(d.parent_item_group or None, []).append(d)
	
	non_unique_filtered_item_group = []
	filtered_item_group = []

	def add_to_list(parent, level):

		if level < depth:
			children = parent_children_map.get(parent) or []
			sort_item_group(children, is_root=True if parent==None else False)

			for child in children:
				child.indent = level
				if child.get('name') not in non_unique_filtered_item_group:
					filtered_item_group.append(child)
					non_unique_filtered_item_group.append(child.name)
				add_to_list(child.name, level + 1)

	add_to_list(None, 0)

	return filtered_item_group

def sort_item_group(item_group, is_root=False, key="name"):

	def compare_item_groups(a, b):
		return cmp(a[key], b[key]) or 1

	item_group.sort(key = functools.cmp_to_key(compare_item_groups))

def prepare_data(filters,item_group):
	data = []

	for d in item_group:
		# add to output
		row = frappe._dict({
			"item_code": _(d.item_code or ''),
			"item_group": _(d.item_name or d.name),
			"parent_item_group": _(d.parent_item_group),
			"indent": flt(d.indent),
			"bom_name":_(d.bom_name),
			"raw_material_cost":flt(d.raw_material_cost,2),
			"total_operational_cost":flt(d.total_operational_cost,2),
			"total_cost":flt(d.total_cost,2),
			"price_list_rate": flt(d.price_list_rate,2),
			"margin": flt(d.margin),
			"is_group": d.is_group
		})
		data.append(row)
	return data

def get_final_out(filters, out):
	data = []
	item_group_map = get_group_map(out)
	for row in out:
		if row.is_group and item_group_map.get(row.item_group):
			row.raw_material_cost = flt(item_group_map.get(row.item_group).raw_material_cost,2)
			row.total_operational_cost = flt(item_group_map.get(row.item_group).total_operational_cost,2)
			row.total_cost = flt(item_group_map.get(row.item_group).total_cost,2)

		if not filters.get('show_0_qty_data'):
			if row.raw_material_cost > 0 or row.total_operational_cost > 0 or row.total_cost > 0:
				data.append(row)
		else:
			data.append(row)
	return data

def get_group_map(out):
	sorted_out = sorted(out, key = lambda i: (i['indent'],i['parent_item_group']),reverse=True)
	item_group_map = {}		

	for row in sorted_out:
		if row.is_group ==1 and item_group_map.get(row.item_group):
			row.raw_material_cost = item_group_map.get(row.item_group).raw_material_cost
			row.total_operational_cost = item_group_map.get(row.item_group).total_operational_cost
			row.total_cost = item_group_map.get(row.item_group).total_cost
		if row.parent_item_group:
			item_group_map.setdefault(row.parent_item_group, frappe._dict({
					"raw_material_cost": 0.0,
					"total_operational_cost": 0.0,
					"total_cost":0.0
				}))
			item_group_dict = item_group_map[row.parent_item_group]
			item_group_dict.raw_material_cost += flt(row.raw_material_cost)
			item_group_dict.total_operational_cost += flt(row.total_operational_cost)
			item_group_dict.total_cost += flt(row.total_cost)
	
	return item_group_map

def get_columns(filters):
	columns = [
		{
			"fieldname": "item_group",
			"label": ("Item Group"),
			"fieldtype": "Data",
			"options": "Item Group",
			"width": 350
		},
		{
			"fieldname": "bom_name",
			"label": ("BOM"),
			"fieldtype": "Link",
			"options":"BOM",
			"width": 150
		},
		{
			"fieldname": "raw_material_cost",
			"label": ("Raw Material Cost"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_operational_cost",
			"label": "Operational Cost",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_cost",
			"label": "Total Cost",
			"fieldtype": "Currency",
			"width": 150
		},]

	if filters.get('price_list'):
		columns +=[
			{
				"fieldname": "price_list_rate",
				"label": "Price List Rate",
				"fieldtype": "Currency",
				"width": 150
			},
			{
				"fieldname": "margin",
				"label": "Margin",
				"fieldtype": "Percent",
				"width": 150
			},
		]
	return columns