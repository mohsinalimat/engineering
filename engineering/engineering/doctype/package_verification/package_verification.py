# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint,cstr, get_url_to_form


class PackageVerification(Document):
	def on_submit(self):
		if self.packages_detail:
			for d in self.packages_detail:
				doc = frappe.get_doc("Item Packing",d.package)
				if self.company != d.company:
					frappe.throw("Row {}: Company doesn't not Match".format(d.idx))
				if d.status == "Inactive":
					frappe.throw("Row {}: Please Create Purchase Receipt for the Stock Balance.".format(d.idx),title="Stock Balance Error")
				if doc.package_verification:
					frappe.throw("Row {}: Package no : {} is already verified.".format(d.idx,d.package))
				else:
					doc.db_set('package_verification',1,update_modified=False)
					doc.db_update()
	
	def on_cancel(self):
		if self.packages_detail:
			for d in self.packages_detail:
				doc = frappe.get_doc("Item Packing",d.package)
				doc.db_set('package_verification',0,update_modified=False)
				doc.db_update()

@frappe.whitelist()
def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()][0]

@frappe.whitelist()
def create_stock_entry(name):
	doc = frappe.get_doc("Package Verification",name)
	if doc.company and doc.packages_detail:
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Send Serialized Item"
		se.company = doc.from_company
		se.send_to_company = 1
		se.job_work_company = doc.company
		se.to_company_receive_warehouse = doc.to_company_receive_warehouse
		item_found = 1
		item_warehouse_dict = {}
		for row in doc.packages_detail:	
			if row.status == "Inactive":
				continue
			item_warehouse_dict.setdefault((row.item_code,row.warehouse), frappe._dict({
				"qty" : 0,"serial_no" : ""
			}))
			item_warehouse_dict[row.item_code, row.warehouse].qty += row.no_of_items
			item_warehouse_dict[row.item_code, row.warehouse].serial_no += "\n"+ row.serial_no
		print(item_warehouse_dict)
		for item,value in item_warehouse_dict.items():
			se.append("items",{
				'item_code': item[0],
				's_warehouse': item[1],
				'serial_no': value.serial_no.strip(),
				'qty': value.qty,
			})
			# item_warehouse_dict_qty[row.item_code,row.warehouse] = row.no_of_items
			# item_warehouse_dict_serial_no[row.item_code,row.warehouse].append(serial_no)
		# for row in doc.packages_detail:
		# 	if row.status == "Inactive":
		# 		continue
		# 	if se.get('items'):
		# 		for se_item in se.items:
		# 			if se_item.item_code == row.item_code and se_item.s_warehouse == row.warehouse:
		# 				se_item.serial_no += "\n" + row.serial_no
		# 				se_item.qty += row.no_of_items
		# 			else:
		# 				item_found = 0
		# 	else:
		# 		item_found = 0

		# 	if item_found == 0:
		# 		se.append("items",{
		# 			'item_code': row.item_code,
		# 			's_warehouse': row.warehouse,
		# 			'serial_no': row.serial_no,
		# 			'qty': row.no_of_items,
		# 		})
		se.save()
		se.submit()
		url = get_url_to_form("Stock Entry", se.name)
		frappe.msgprint(_("Stock Entry <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=frappe.bold(se.name))), title="Stock Enttry Created", indicator="green")