# Copyright (c) 2013, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_data(filters):

	query = frappe.db.sql("""
	select
		ip.name as package_no, ip.item_code, ip.item_group,sno.warehouse,ip.no_of_items, sno.company, sno.status, ip.serial_no, ip.item_name
	from
		`tabItem Packing` as ip JOIN
		`tabSerial No` as sno on sno.name = SUBSTRING_INDEX(ip.serial_no,'\n',1)
	where
		sno.status = 'Active' and ip.docstatus = 1{}
	""".format(get_conditions(filters)))
	return query

def get_conditions(filters):
	condition = ""
	condition += " and ip.package_verification = '%s'" % filters.verified

	if filters.get("company"):
		condition += " and sno.company = '%s'" % filters.company
	if filters.get("item_code"):
		condition += " and ip.item_code = '%s'" % filters.item_code
	if filters.get("item_group"):
		condition += " and ip.item_group = '%s'" % filters.item_group
	if filters.get("warehouse"):
		condition += " and sno.warehouse = '%s'" % filters.warehouse
	if filters.get('to_date'):
		condition += " and ip.posting_date <= '%s'" % filters.to_date
	return condition

def get_columns(filters):
	columns = [{"label": _("Package No"), "fieldname": "package_no", "fieldtype": "Link", "options": "Item Packing","width": 120},
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype":"Link","options": "Item","width": 120},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype":"Link","options": "Item Group","width": 120},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 200},
		{"label": _("No of Pcs"), "fieldname": "no_of_items", "fieldtype": "Float","width": 80},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link","options": "Company","width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data","width": 120},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Data","width": 200},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype":"Data","width": 120},
	]
	return columns
