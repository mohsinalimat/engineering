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
from random import random
import re

class SerialNoGenerator(Document):
	
	def validate(self):
		if cint(self.from_value) > cint(self.to_value):
			frappe.throw(_("From Value Cannot be greater than To Value"))
		code = len(cstr(self.to_value))
		
		if code > 8:
			frappe.throw("Please Enter Low From And To Value")
		
		serial_no = self.serial_no_series + getseries(self.series, 8, cint(self.from_value))
		if frappe.db.exists("Serial No", serial_no):
			frappe.throw("Serial No {} for naming series {} already exists".format(frappe.bold(serial_no), frappe.bold(serial_no)))	

	def on_submit(self):
		self.enqueue_serial_no()
		frappe.db.sql("update `tabSeries` set current = {} where name = '{}'".format(self.to_value, self.serial_no_series))

	def enqueue_serial_no(self): 
		enqueue(self.generate_serial_no, queue='default',timeout=6000, job_name='serial_no_genration')

	def generate_serial_no(self):
		values = []
		user = frappe.session.user
		for item in range(cint(self.from_value), cint(self.to_value) + 1):
			serial_no = self.serial_no_series + getseries(self.series, 8, item)
			qr_code_hash = frappe.generate_hash(length = 16)
			sr_no = ''.join(filter(lambda i: i.isdigit(), serial_no))
			sr_no_info = sr_no[-9:]
			while re.search('[eE]',qr_code_hash):
				qr_code_hash = frappe.generate_hash(length = 16)
			while not re.search('[a-zA-Z]', qr_code_hash):
				qr_code_hash = frappe.generate_hash(length = 16)
				while re.search('[eE]',qr_code_hash):
					qr_code_hash = frappe.generate_hash(length = 16)
			time = frappe.utils.get_datetime()
			values.append((serial_no, time, time , user, user,serial_no, sr_no_info,qr_code_hash))
			if item % 25000 == 0:
				bulk_insert("Serial No", fields=['name', "creation", "modified", "modified_by", "owner", 'serial_no', 'sr_no_info','qr_code_hash'], values=values)
				frappe.db.commit()
				values =[]
		if values != []:
			values.append((123, time, time , user, user,123, 123,'18494526296'))
			frappe.db.bulk_insert("Serial No", fields=['name', "creation", "modified", "modified_by", "owner", 'serial_no', 'sr_no_info','qr_code_hash'], values=values)
			frappe.db.commit()

def bulk_insert(doctype, fields, values, ignore_duplicates=False):
	"""
		Insert multiple records at a time
		:param doctype: Doctype name
		:param fields: list of fields
		:params values: list of list of values
	"""
	insert_list = []
	fields = ", ".join(["`"+field+"`" for field in fields])

	for idx, value in enumerate(values):
		insert_list.append(tuple(value))
		if idx and (idx%10000 == 0 or idx < len(values)):
			frappe.db.sql("""INSERT {ignore_duplicates} INTO `tab{doctype}` ({fields}) VALUES {values}""".format(
					ignore_duplicates="IGNORE" if ignore_duplicates else "",
					doctype=doctype,
					fields=fields,
					values=", ".join(['%s'] * len(insert_list))
				), tuple(insert_list))
			insert_list = []

def getseries(key, digits, current):
	return ('%0'+str(digits)+'d') % current