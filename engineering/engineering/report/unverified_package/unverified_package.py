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
		ip.name as package_no, ip.item_code, sno.warehouse, ip.no_of_items, ip.company, sno.status, ip.serial_no
	from
		`tabItem Packing` as ip JOIN
		`tabSerial No` as sno on sno.name = SUBSTRING_INDEX(ip.serial_no,'\n',1)
	where
		ip.package_verification = 0 and sno.status = 'Active' and ip.docstatus = 1{}
	""".format(get_conditions(filters)))
	return query

def get_conditions(filters):
	condition = ""
	if filters.get("company"):
		condition = " and ip.company = '%s'" % filters.company
	return condition

def get_columns(filters):
	columns = [{"label": _("Package No"), "fieldname": "package_no", "fieldtype": "Link", "options": "Item Packing","width": 120},
		{"label": _("Item Code"), "fieldname": "item_code", "options": "Item","width": 120},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 200},
		{"label": _("No of Pcs"), "fieldname": "no_of_items", "fieldtype": "Float","width": 80},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link","options": "Company","width": 220},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data","width": 120},
		{"label": _("Serial No"), "fieldname": "serial_no", "fieldtype": "Data","width": 200},
	]
	return columns
