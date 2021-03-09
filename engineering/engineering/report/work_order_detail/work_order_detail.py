# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import re
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{"label": _("Name"), "fieldname": "name", "fieldtype": "Link", "options": "Work Order", "width": 150},
		{"label": _("Date"), "fieldname": "planned_start_date", "fieldtype": "Date", "width": 150},
		{"label": _("Qty To Manufacture"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Transffered qty"), "fieldname": "transferred_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Consumed qty"), "fieldname": "consumed_qty", "fieldtype": "Float", "width": 120},
		{"label": _("Difference"), "fieldname": "difference", "fieldtype": "Float", "width": 120},
	]
	return columns

def get_data(filters):
	# getting data from filters
	production_item = re.escape(filters.get("production_item", ""))
	company = re.escape(filters.get("company", ""))
	from_date = filters.get("from_date", None)
	to_date = filters.get("to_date", None)
	
	# adding where condition according to filters
	condition = ''
	format_ = '%Y-%m-%d %H:%M:%S'
	if from_date:
		condition += "AND DATE(wo.planned_start_date) >= '{}' \n".format(str(from_date))
		
	if to_date:
		condition += "AND DATE(wo.planned_start_date) <= '{}' \n".format(str(to_date))

	if production_item:
		condition += "AND wo.production_item = '{}' \n".format(production_item)
	
	if company:
		condition += "AND wo.company = '{}' \n".format(company)
	
	# sql query to get data for column
	data = frappe.db.sql("""SELECT 
	wo.planned_start_date as planned_start_date, 
	wo.name as name,
	wo.production_item,
	wo.qty as qty,
	woi.item_code as item_code,
	woi.transferred_qty as transferred_qty,
	woi.consumed_qty as consumed_qty,
	(woi.transferred_qty - woi.consumed_qty) as difference
	FROM  `tabWork Order` as wo
	LEFT JOIN `tabWork Order Item` as woi ON woi.parent = wo.name 
	WHERE wo.docstatus = 1
	{}
	""".format(condition), as_dict=1)
	return data