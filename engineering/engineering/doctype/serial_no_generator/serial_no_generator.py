# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr
from frappe.model.naming import make_autoname
from frappe import enqueue

class SerialNoGenerator(Document):
	
	def validate(self):
		if cint(self.from_value) > cint(self.to_value):
			frappe.throw(_("From Value Cannot be greater than To Value"))
		code = len(cstr(self.to_value))
		
		if code > 8:
			frappe.throw("Please Enter Low From And To Value")
		
		serial_no = self.serial_no_series + getseries(self.series, 8, cint(self.from_value))
		if frappe.db.exists("Serial No", serial_no):
			frappe.throw("Serial No {} for naming series {} already exists".format(frappe.bold(item), frappe.bold(serial_no)))	

	def on_submit(self):
		self.enqueue_serial_no()


	def enqueue_serial_no(self): 
		enqueue(self.generate_serial_no)

	def generate_serial_no(self):
		frappe.publish_realtime('msgprint', 'Starting long job...')
		for item in range(cint(self.from_value), cint(self.to_value) + 1):
			serial_no = self.serial_no_series + getseries(self.series, 8, item)
			
			doc = frappe.new_doc("Serial No")
			doc.serial_no = serial_no
			doc.qr_code_hash = frappe.generate_hash(length = 16)
			doc.save()
		frappe.db.sql("update `tabSeries` set current = {} where name = '{}'".format(self.to_value, self.serial_no_series))
		frappe.publish_realtime('msgprint', 'Ending long job...')

def getseries(key, digits, current):
	return ('%0'+str(digits)+'d') % current