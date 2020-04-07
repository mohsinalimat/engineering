# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cint

from engineering.api import before_naming as bn

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class ItemPacking(Document):
	def on_update(self):
		self.submit()
		
	def on_submit(self):
		serial_no = get_serial_nos(self.serial_no)

		if len(serial_no) > cint(frappe.db.get_value("Item", self.item_code,'qty_per_box')):
			frappe.throw(f"Cannot Have More than {cint(frappe.db.get_value('Item', self.item_code ,'qty_per_box'))} item in box")

		serial_no_check = []
		for item in serial_no:
			if item not in serial_no_check:
				serial_no_check.append(item)
			else:
				frappe.throw("You can not add same serial number more than once")

		self.create_serial_no(serial_no)

		if self.include_for_manufacturing:
			se = frappe.new_doc("Stock Entry")
			se.stock_entry_type = 'Manufacture'
			se.company = self.company
			se.purpose = 'Manufacture'
			se.set_posting_time = 1
			se.posting_date = self.posting_date
			se.posting_time = self.posting_time
			se.from_bom = 1
			se.work_order = self.work_order
			se.bom_no = self.bom_no
			se.fg_completed_qty = len(serial_no)
			se.from_warehouse = frappe.db.get_value("Work Order", self.work_order, 'wip_warehouse')
			se.to_warehouse = frappe.db.get_value("Work Order", self.work_order, 'fg_warehouse')
			
			se.get_items()
			# se.save()
			for item in se.items:
				if item.item_code == self.item_code:
					item.serial_no = self.serial_no
					item.t_warehouse = se.to_warehouse
					item.qty = len(serial_no)
			se.reference_doctype = "Item Packing"
			se.reference_docname = self.name
			se.save()
			
			se.save()
			se.submit()
		
		self.submit()
	
	def on_cancel(self):
		serial_no = get_serial_nos(self.serial_no)

		for item in serial_no:
			sr = frappe.get_doc("Serial No", item)

			sr.box_serial_no = ''
			sr.save()
		if self.include_for_manufacturing:
			if frappe.db.exists("Stock Entry", {'reference_doctype': 'Item Packing', 'reference_docname': self.name, 'docstatus': 1}):
				doc = frappe.get_doc("Stock Entry", {'reference_doctype': 'Item Packing', 'reference_docname': self.name, 'docstatus': 1})
				doc.flags.ignore_permissions = True
				doc.cancel()

	def create_serial_no(self, serial_no):
		for item in serial_no:
			args = {
				"warehouse": self.warehouse,
				"item_code": self.item_code,
				"company": self.company,
				"box_serial_no": self.name
			}

			make_serial_no(self, item, args)
	
	def print_package(self, commit=True):
		self.save()
		return self.name


def make_serial_no(self, serial_no, args):
	if frappe.db.exists("Serial No", serial_no):
		sr = frappe.get_doc("Serial No", serial_no)

		if sr.box_serial_no:
			frappe.throw("Serial No {} is already in box {}".format(frappe.bold(serial_no), frappe.bold(sr.box_serial_no)))
	else:
		sr = frappe.new_doc("Serial No")
	
	sr.serial_no = serial_no
	sr.company = args.get('company')
	sr.item_code = args.get('item_code')
	sr.flags.ignore_permissions = True
	sr.box_serial_no = self.name

	if not frappe.db.exists("Serial No", serial_no):
		sr.insert()
	
	sr.save()

	return sr.name

@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Item Packing", docname)
	# frappe.throw(doc.name)
	doc.save()
	doc.submit()