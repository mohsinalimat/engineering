# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, cint, flt, comma_or, getdate, nowdate, formatdate, format_time
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from erpnext.stock.get_item_details import get_bin_details, get_default_cost_center
from erpnext.stock.doctype.stock_entry.stock_entry import get_uom_details,get_warehouse_details
from erpnext.stock.doctype.batch.batch import get_batch_no
from frappe.utils.background_jobs import enqueue, get_jobs
from frappe.utils import cint, flt, getdate, nowdate, add_days

class JobWorkReturn(Document):
	def validate(self):
		for row in self.items:
			row.amount = flt(row.qty) * flt(row.basic_rate)
			row.basic_amount = flt(row.qty) * flt(row.basic_rate)

	def on_submit(self):
#		self.create_stock_entry()
		# self.enqueue_send_jobwork_finish_entry()
		# self.enqueue_jobwork_manufacturing_entry()
		self.enqueue_stock_entry()
		# self.send_jobwork_finish_entry()
		# self.jobwork_manufacturing_entry()

	def on_cancel(self):
		self.cancel_repack_entry()
		self.cancel_material_issue()
		self.db_set('repack_ref', '')
		self.db_set('issue_ref', '')
		

	def create_stock_entry(self):
		pass
		
	# def enqueue_jobwork_manufacturing_entry(self):
	# 	if self.posting_date < add_days(nowdate(), -3):
	# 		queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
	# 		job = "Job Work Manufacturing Entry" + self.name
	# 		if job not in queued_jobs:
	# 			frappe.msgprint(_(" The Stock Entry is of old date. It has been queued in background jobs, may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is in Queue '),indicator="green")
	# 			enqueue(jobwork_manufacturing_entry,queue= "long", timeout= 1800, job_name= job, self= self)
	# 		else:
	# 			frappe.msgprint(_(" Stock Entry Creation is already in queue it may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is Already in Queue '),indicator="green")			
	# 	else:
	# 		jobwork_manufacturing_entry(self= self)
	# 		frappe.msgprint("Stock Entry For this Item has been Created")		

	# def enqueue_send_jobwork_finish_entry(self):
		# if self.posting_date < add_days(nowdate(), -3):
		# 	queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
		# 	job = "Job Work Finish Entry" + self.name
		# 	if job not in queued_jobs:
		# 		frappe.msgprint(_(" The Stock Entry is of old date. It has been queued in background jobs, may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is in Queue '),indicator="green")
		# 		enqueue(send_jobwork_finish_entry,queue= "long", timeout= 1800, job_name= job, self= self)
		# 	else:
		# 		frappe.msgprint(_(" Stock Entry Creation is already in queue it may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is Already in Queue '),indicator="green")			
		# else:
		# 	send_jobwork_finish_entry(self= self)
		# 	frappe.msgprint("Stock Entry For this Item has been Created")

	def enqueue_stock_entry(self):
		if self.posting_date < add_days(nowdate(), -3):
			queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
			job_finish = "Job Work Finish Entry" + self.name
			job_manufacture = "Job Work Manufacturing Entry" + self.name
			if job_finish not in queued_jobs and job_manufacture not in queued_jobs:
				frappe.msgprint(_(" The Stock Entry is of old date. It has been queued in background jobs, may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is in Queue '),indicator="green")
				enqueue(send_jobwork_finish_entry,queue= "long", timeout= 1800, job_name= job_finish, self= self)
				enqueue(jobwork_manufacturing_entry,queue= "long", timeout= 1800, job_name= job_manufacture, self= self)
			else:
				frappe.msgprint(_(" Stock Entry Creation is already in queue it may take 15-20 minutes to complete. Please don't re-create check it after 20 minute, if not created call finbyz "),title=_(' Stock Entry creation job is Already in Queue '),indicator="green")			
		else:
			send_jobwork_finish_entry(self= self)
			jobwork_manufacturing_entry(self= self)
			frappe.msgprint("Stock Entry For this Item has been Created")

	def cancel_repack_entry(self):
		if frappe.db.exists("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name,'company': self.job_work_company}):
			se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name,'company': self.job_work_company})
			se.flags.ignore_permissions = True
			if se.docstatus == 1:
				se.cancel()
			se.db_set('reference_doctype','')
			se.db_set('reference_docname','')


	def cancel_material_issue(self):
		if frappe.db.exists("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name,'company': self.company}):
			mi = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name,'company': self.company})
			mi.flags.ignore_permissions = True
			if mi.docstatus == 1:
				mi.cancel()
			mi.db_set('reference_doctype','')
			mi.db_set('reference_docname','')

	def get_item_details(self, args=None, for_update=False):
		item = frappe.db.sql("""select i.name, i.stock_uom, i.description, i.image, i.item_name, i.item_group,
				i.has_batch_no, i.sample_quantity, i.has_serial_no,
				id.expense_account, id.buying_cost_center
			from `tabItem` i LEFT JOIN `tabItem Default` id ON i.name=id.parent and id.company=%s
			where i.name=%s
				and i.disabled=0
				and (i.end_of_life is null or i.end_of_life='0000-00-00' or i.end_of_life > %s)""",
			(self.company, args.get('item_code'), nowdate()), as_dict = 1)

		if not item:
			frappe.throw(_("Item {0} is not active or end of life has been reached").format(args.get("item_code")))

		item = item[0]
		item_group_defaults = get_item_group_defaults(item.name, self.company)
		brand_defaults = get_brand_defaults(item.name, self.company)

		ret = frappe._dict({
			'uom'			      	: item.stock_uom,
			'stock_uom'				: item.stock_uom,
			'description'		  	: item.description,
			'image'					: item.image,
			'item_name' 		  	: item.item_name,
			'cost_center'			: get_default_cost_center(args, item, item_group_defaults, brand_defaults, self.company),
			'qty'					: args.get("qty"),
			'transfer_qty'			: args.get('qty'),
			'conversion_factor'		: 1,
			'batch_no'				: '',
			'actual_qty'			: 0,
			'basic_rate'			: 0,
			'serial_no'				: '',
			'has_serial_no'			: item.has_serial_no,
			'has_batch_no'			: item.has_batch_no,
			'sample_quantity'		: item.sample_quantity
		})

		# update uom
		if args.get("uom") and for_update:
			ret.update(get_uom_details(args.get('item_code'), args.get('uom'), args.get('qty')))

		for company_field, field in {'stock_adjustment_account': 'expense_account',
			'cost_center': 'cost_center'}.items():
			if not ret.get(field):
				ret[field] = frappe.get_cached_value('Company',  self.company,  company_field)

		args['posting_date'] = self.posting_date
		args['posting_time'] = self.posting_time

		stock_and_rate = get_warehouse_details(args) if args.get('warehouse') else {}
		ret.update(stock_and_rate)

		# automatically select batch for outgoing item
		if (args.get('s_warehouse', None) and args.get('qty') and
			ret.get('has_batch_no') and not args.get('batch_no')):
			args.batch_no = get_batch_no(args['item_code'], args['s_warehouse'], args['qty'])

		return ret

def send_jobwork_finish_entry(self):
	# create material issue
	mi = frappe.new_doc("Stock Entry")
	mi.stock_entry_type = "Send Jobwork Finish"
	mi.purpose = "Material Issue"
	mi.set_posting_time = 1
	mi.reference_doctype = self.doctype
	mi.reference_docname = self.name
	mi.company = self.company
	mi.posting_date = self.posting_date
	mi.posting_time = self.posting_time
	mi.send_to_company = 1
	mi.job_work_company = self.job_work_company
	
	source_abbr = frappe.db.get_value("Company", self.company,'abbr')
	target_abbr = frappe.db.get_value("Company", self.job_work_company,'abbr')
	
	mi.append("items",{
		'item_code': self.item_code,
		's_warehouse': self.jobwork_in_warehouse,
		'batch_no': self.batch_no,
		'serial_no': self.serial_no,
		'qty': self.qty,
		'cost_center': frappe.db.get_value("Company",self.company,'cost_center') or 'Main - {0}'.format(source_abbr)
	})
	
	for row in self.additional_cost:
		mi.append("additional_costs",{
			'expense_account': row.expense_account,
			'description': row.description,
			'amount': row.amount
		})

	mi.save(ignore_permissions=True)
	
	# mi.update_stock_ledger()
	mi.save(ignore_permissions=True)
	mi.submit()
	self.db_set('issue_ref',mi.name)
	self.issue_ref = mi.name

def jobwork_manufacturing_entry(self):
	#create repack
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Jobwork Manufacturing"
	se.purpose = "Repack"
	se.set_posting_time = 1
	se.reference_doctype = self.doctype
	se.reference_docname =self.name
	se.posting_date = self.posting_date
	se.posting_time = self.posting_time
	se.company = self.job_work_company
	source_abbr = frappe.db.get_value('Company',self.company,'abbr')
	target_abbr = frappe.db.get_value('Company',self.job_work_company,'abbr')
	for row in self.items:
		se.append("items",{
			'item_code': row.item_code,
			's_warehouse': self.s_warehouse,
			'batch_no': row.batch_no,
			'serial_no': row.serial_no,
			'qty': row.qty,
		})
		se.append("items",{
			'item_code': self.item_code,
			't_warehouse': self.t_warehouse,
			'batch_no': self.batch_no,
			'serial_no': self.serial_no,
			'qty': self.qty,
		})
	for row in self.additional_cost:
		se.append("additional_costs",{
			'expense_account': row.expense_account.replace(source_abbr,target_abbr),
			'description': row.description,
			'amount': row.amount
		})
	se.save(ignore_permissions=True)
	se.get_stock_and_rate()
	se.save(ignore_permissions=True)
	se.submit()
	self.db_set('repack_ref',se.name)
	self.repack_ref = se.name
