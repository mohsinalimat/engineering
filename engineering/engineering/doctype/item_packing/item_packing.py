# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class ItemPacking(Document):
	def on_update(self):
		self.submit()
		
	def on_submit(self):
		serial_no = get_serial_nos(self.serial_no)

		serial_no_check = []
		for item in serial_no:
			if item not in serial_no_check:
				serial_no_check.append(item)
			else:
				frappe.throw("You can not add same serial number more than once")

		qty_per_box = frappe.db.get_value("Item", self.box_item, 'qty_per_box')

		if not qty_per_box:
			frappe.throw("Please add Qty Per Box in Box Item")

		if len(serial_no) > qty_per_box:
			frappe.throw("Item in this box cannot be grater that {}".format(qty_per_box))
		self.create_serial_no(serial_no)
		
		self.submit()
	
	def on_cancel(self):
		serial_no = get_serial_nos(self.serial_no)

		for item in serial_no:
			sr = frappe.get_doc("Serial No", item)

			sr.box_serial_no = ''
			sr.save()

	def create_serial_no(self, serial_no):
		for item in serial_no:
			args = {
				"warehouse": self.warehouse,
				"item_code": self.item_code,
				"company": self.company,
				"box_serial_no": self.name
			}

			make_serial_no(item, args)

def make_serial_no(serial_no, args):
	if frappe.db.exists("Serial No", serial_no):
		sr = frappe.get_doc("Serial No", serial_no)
	else
		sr = frappe.new_doc("Serial No")
		sr.serial_no = serial_no
		sr.company = args.get('company')
	
	sr.item_code = args.get('item_code')
	sr.flags.ignore_permissions = True
	sr.box_serial_no = args.get('box_serial_no')

	sr.insert()
	sr.save()

	return sr.name

@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Item Packing", docname)
	# frappe.throw(doc.name)
	doc.save()
	doc.submit()