# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate, add_days, cstr
from engineering.api import before_naming as bn
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from datetime import timedelta, datetime, date
from frappe.utils.background_jobs import enqueue, get_jobs
from random import random
import re

class ItemPacking(Document):
	def validate(self):
		self.validate_serial_no()

	def validate_serial_no(self):
		specialchars = '[@_!#$\\\\"\'%^&*()<>?/|}{~:]'
		regex = re.compile(specialchars)
		if(regex.search(self.serial_no)):
			frappe.throw("Special characters like <b> < > ? / ; : \' \" { } [ ] | \\ # $ % ^ ( ) * + </b> are not allowed in Serial No!", title="Invalid Characters")

	def before_validate(self):
		values = []
		user = frappe.session.user
		if self.auto_create_serial_no and not self.serial_no:
			serial_no_series = frappe.db.get_value("Item",self.item_code,'serial_no_series')
			if not serial_no_series:
				frappe.throw("Please Add Serial Number Series In Item: " + str(self.item_code))
			else:
				self.serial_no = get_auto_serial_nos(serial_no_series,self.qty_per_box)

					# serial_no = serial_no_series + getseries(8, item)
					# if frappe.db.exists("Serial No", serial_no):
					# 	sr_no = frappe.db.sql("select sr_no_info from `tabSerial No` where item_code = '{}' and name LIKE '%{}%' ORDER BY sr_no_info DESC limit 1".format(self.item_code,serial_no_series))[0][0]
					# 	zero_digit = 8 - len(str(sr_no))
					# 	serial_no_with_zeros = serial_no_series.ljust(zero_digit + len(serial_no_series),'0')
					# 	serial_no = serial_no_with_zeros + str(sr_no + 1)

					# sr_no = ''.join(filter(lambda i: i.isdigit(), serial_no))
					# sr_no_info = sr_no[-9:]
					# qr_code_hash = frappe.generate_hash(length = 16)
					# while re.search('[eE]',qr_code_hash):
					# 	qr_code_hash = frappe.generate_hash(length = 16)
					# while not re.search('[a-zA-Z]', qr_code_hash):
					# 	qr_code_hash = frappe.generate_hash(length = 16)
					# 	while re.search('[eE]',qr_code_hash):
					# 		qr_code_hash = frappe.generate_hash(length = 16)		
					# time = frappe.utils.get_datetime()
					# doc = frappe.new_doc("Serial No")
					# doc.serial_no = serial_no_series
					# doc.creation = time
					# doc.modified = time
					# doc.modified_by = user
					# doc.owner = user
					# doc.sr_no_info = sr_no_info
					# doc.qr_code_hash = qr_code_hash
					# doc.item_code = self.item_code
					# doc.company = self.company
					# doc.db_insert()
					# ip_serial_no += doc.name + "\n"
				# 	values.append((serial_no, time, time , user, user,serial_no, sr_no_info,qr_code_hash,self.item_code,self.warehouse or None,self.company))
				# if values !=[]:
				# 	frappe.db.bulk_insert("Serial No", fields=['name', "creation", "modified", "modified_by", "owner", 'serial_no', 'sr_no_info','qr_code_hash','item_code','warehouse','company'], values=values)
				# 	values = []

	def on_update(self):
		serial_no = get_serial_nos(self.serial_no)
		self.no_of_items = len(serial_no)
		self.not_yet_manufactured = 1
		if self.work_order:
			self.no_of_item_work_order = get_work_order_manufactured_qty(self.work_order)

		self.submit()

	def on_submit(self):
		if self.work_order:
			if self.item_code != frappe.db.get_value("Work Order",self.work_order,'production_item'):
				frappe.throw("Work Order Item is Different than Current Item")
			wo_planned_date = frappe.get_value("Work Order",self.work_order,'planned_start_date')
			wo_date = datetime.strftime(wo_planned_date,'%Y-%m-%d %H:%M:%S')
			if str(self.posting_date + " " + self.posting_time) < str(wo_date):
				frappe.throw("Posting Date and Posting Time should not be before Work Order start date and time")

		serial_no = get_serial_nos(self.serial_no)

		if len(serial_no) != cint(frappe.db.get_value("Item", self.item_code,'qty_per_box')):
			frappe.throw(f"Cannot Have More than {cint(frappe.db.get_value('Item', self.item_code ,'qty_per_box'))} item in box")

		serial_no_check = []
		for item in serial_no:
			if item not in serial_no_check:
				serial_no_check.append(item)
			else:
				frappe.throw("You can not add same serial number more than once")

		self.create_serial_no(serial_no)
		self.submit()
		# if self.include_for_manufacturing:
			# from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
			# se = frappe.new_doc("Stock Entry")
			# se.update(make_stock_entry(self.work_order,"Manufacture", qty=self.no_of_items))
			# se.set_posting_time = 1
			# se.posting_date = self.posting_date
			# se.posting_time = self.posting_time
			# se.from_warehouse = frappe.db.get_value("Work Order", self.work_order, 'wip_warehouse')
			# se.to_warehouse = frappe.db.get_value("Work Order", self.work_order, 'fg_warehouse')
			
			# # se.save()
			# for item in se.items:
			# 	if item.item_code == self.item_code:
			# 		item.serial_no = self.serial_no
			# 		item.t_warehouse = se.to_warehouse
			# 		item.qty = self.no_of_items
			# se.reference_doctype = "Item Packing"
			# se.reference_docname = self.name
			# se.save()
			# se.submit()
		

		
	def before_cancel(self):
		if self.include_for_manufacturing:
			if frappe.db.exists("Stock Entry", {'from_item_packing':1,'name':self.stock_entry, 'docstatus': 1}):
				frappe.throw("Please Cancel Stock Entry before cancelling this Item Packing")

	def on_cancel(self):
		serial_no = get_serial_nos(self.serial_no)

		for item in serial_no:
			sr = frappe.get_doc("Serial No", item)

			sr.box_serial_no = ''
			sr.save()
		# if self.include_for_manufacturing:
		# 	if frappe.db.exists("Stock Entry", {'reference_doctype': 'Item Packing', 'reference_docname': self.name, 'docstatus': 1}):
		# 		doc = frappe.get_doc("Stock Entry", {'reference_doctype': 'Item Packing', 'reference_docname': self.name, 'docstatus': 1})
		# 		doc.flags.ignore_permissions = True
		# 		doc.cancel()

	def create_serial_no(self, serial_no):
		for item in serial_no:
			args = {
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
		if sr.item_code and sr.item_code != self.item_code:
			frappe.throw("Serial No exists with different Item code")
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
		sr.insert(ignore_permissions=True)
	
	sr.save()

	return sr.name

@frappe.whitelist()
def submit_form(docname):
	doc = frappe.get_doc("Item Packing", docname)
	# frappe.throw(doc.name)
	doc.save()
	doc.submit()

@frappe.whitelist()
def enqueue_stock_entry(work_order, posting_date, posting_time):
	queued_jobs = get_jobs(site = frappe.local.site,key='job_name')[frappe.local.site]
	job = "Stock Entry from Item Packing " + work_order
	if job not in queued_jobs:
		frappe.msgprint(_(" The Stock Entry has been queued in background jobs, may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is in Queue '),indicator="green")
		enqueue(make_stock_entry,queue= "long", timeout= 1800, job_name= job, work_order= work_order, posting_date= posting_date, posting_time= posting_time)
	else:
		frappe.msgprint(_(" Stock Entry Creation is already in queue it may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is Already in Queue '),indicator="green")			

@frappe.whitelist()
def make_stock_entry(work_order = None, posting_date = None, posting_time = None):
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
	filters = {'include_for_manufacturing': 1, 'not_yet_manufactured': 1, 'docstatus': 1}
	if work_order:
		filters['work_order'] = work_order
	for i in frappe.get_all("Item Packing", filters, ['distinct work_order as work_order']):
		serial_no_list = []
		no_of_items = 0
		name_list = []
		for j in frappe.get_list("Item Packing", {'include_for_manufacturing': 1, 'not_yet_manufactured': 1, 'work_order': i.work_order, 'docstatus': 1}, ['name', 'serial_no', 'no_of_items']):
			serial_no_list.append(j.serial_no)
			no_of_items += j.no_of_items
			name_list.append(j.name)
		
		
		if no_of_items:
			serial_no = '\n'.join(serial_no_list)

			se = frappe.new_doc("Stock Entry")
			se.update(make_stock_entry(i.work_order,"Manufacture", qty=no_of_items))
			
			if posting_date and posting_time:
				se.set_posting_time = 1
				se.posting_date = posting_date
				se.posting_time = posting_time
				se.from_item_packing = 1
			
			se.from_warehouse = frappe.db.get_value("Work Order", i.work_order, 'wip_warehouse')
			se.to_warehouse = frappe.db.get_value("Work Order", i.work_order, 'fg_warehouse')
			# se.save()	
			for item in se.items:
				if item.item_code == frappe.db.get_value("Work Order",i.work_order,'production_item'):
					item.t_warehouse = se.to_warehouse
					item.qty = no_of_items
					item.serial_no = serial_no
			
			se.save()
			se.submit()
		
			for j in name_list:
				doc = frappe.get_doc("Item Packing",j)
				doc.db_set("stock_entry",se.name, update_modified=False)
				doc.db_set("not_yet_manufactured",0, update_modified=False)
			return "Manufactuing Entry For this Item has been Created."

@frappe.whitelist()
def enqueue_material_receipt(warehouse, item_code, company, posting_date, posting_time):
	if not warehouse:
		frappe.throw("Please Enter Warehouse")
	queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
	job = "Material Receipt from Item Packing "+item_code
	if job not in queued_jobs:
		frappe.msgprint(_(" The Material Receipt has been queued in background jobs, may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Material Receipt creation job is in Queue '),indicator="green")
		enqueue(make_material_receipt,queue= "long", timeout= 1800, job_name= job, warehouse= warehouse, item_code=item_code, company= company, posting_date= posting_date, posting_time= posting_time)
	else:
		frappe.msgprint(_(" Material Receipt Creation is already in queue it may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Material Receipt creation job is Already in Queue '),indicator="green")			

@frappe.whitelist()
def make_material_receipt(warehouse, item_code, company, posting_date = None, posting_time = None):
	serial_no_list = []
	no_of_items = 0
	name_list = []
	item_code_list = []
	query = frappe.db.sql(f"""
		select
			name, item_code, serial_no, no_of_items
		from 
			`tabItem Packing`
		where
			work_order IS NULL and (stock_entry IS NUll or stock_entry = '') and not_yet_manufactured = 1 and docstatus = 1 and company = '{company}' and warehouse = '{warehouse}' and item_code = '{item_code}'
	""", as_dict = True)
	# for j in frappe.get_list("Item Packing", {'item_code': item_code,'not_yet_manufactured': 1, 'docstatus': 1,'company':company, 'warehouse': warehouse}, ['name', 'item_code','serial_no', 'no_of_items']):
	# 	serial_no_list.append(j.serial_no)
	# 	no_of_items += j.no_of_items
	# 	name_list.append(j.name)
	for j in query:
		serial_no_list.append(j.serial_no)
		no_of_items += (j.no_of_items)
		name_list.append(j.name)
	if no_of_items:
		serial_no = '\n'.join(serial_no_list)
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Receipt"
		se.naming_series = "OSTE-.fiscal.company_series.-.####"
		se.company = company
		se.to_warehouse = warehouse
		if posting_date and posting_time:
			se.set_posting_time = 1
			se.posting_date = posting_date
			se.posting_time = posting_time
			se.from_item_packing = 1
		se.append("items",{
			"item_code": item_code,
			"qty": no_of_items,
			"serial_no": serial_no,
			"t_warehouse" : se.to_warehouse
		})
		se.save()
		se.submit()
	
		for j in name_list:
			doc = frappe.get_doc("Item Packing",j)
			doc.db_set("stock_entry",se.name, update_modified=False)
			doc.db_set("not_yet_manufactured",0, update_modified=False)
			#frappe.db.set_value("Item Packing", j, 'stock_entry', se.name)
		return "Material Receipt For this Item has been Created"

@frappe.whitelist()
def get_work_order_manufactured_qty(work_order):
	qty = flt(frappe.db.get_value("Work Order", work_order, 'produced_qty')) or 0

	qty_item_packing = flt(frappe.db.get_value("Item Packing", {'not_yet_manufactured': 1, 'work_order': work_order, 'docstatus': 1}, 'sum(no_of_items)')) or 0
	if qty + qty_item_packing > (flt(frappe.db.get_value("Work Order", work_order, 'qty')) or 0):
		frappe.throw(f"Work Order {work_order} completed.")
	return qty_item_packing + qty

def getseries(digits, current):
	return ('%0'+str(digits)+'d') % current

def get_auto_serial_nos(serial_no_series, qty):
	serial_nos = []
	for i in range(cint(qty)):
		serial_nos.append(make_autoname(serial_no_series, "Serial No"))

	return "\n".join(serial_nos)