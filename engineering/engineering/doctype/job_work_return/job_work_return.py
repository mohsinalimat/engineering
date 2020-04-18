# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JobWorkReturn(Document):
	def validate(self):
		pass

	def on_submit(self):
#		self.create_stock_entry()
		self.send_jobwork_finish_entry()
		self.jobwork_manufacturing_entry()

	def on_cancel(self):
		pass
		#self.cancel_repack_entry()

	def create_stock_entry(self):
		pass
		

	def jobwork_manufacturing_entry(self):
		#create repack
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Jobwork Manufacturing"
		se.purpose = "Repack"
		se.set_posting_time = 1
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.company = self.job_work_company
		
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
				'description': row.description,
				'amount': row.amount
			})
		try:
			se.save(ignore_permissions=True)
			frappe.flags.warehouse_account_map = None
			se.submit()
			self.db_set('repack_ref',se.name)
			self.repack_ref = se.name
		except Exception as e:
			raise e

	def send_jobwork_finish_entry(self):
		# create material issue
		mi = frappe.new_doc("Stock Entry")
		mi.stock_entry_type = "Send Jobwork Finish"
		mi.purpose = "Material Issue"
		mi.set_posting_time = 1
		mi.company = self.company
		mi.posting_date = self.posting_date
		mi.posting_time = self.posting_time
		mi.send_to_company = 1
		mi.job_work_company = self.job_work_company
		#company = frappe.db.get_value("Stock Entry",self.material_transfer,'job_work_company')
		
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
				'description': row.description,
				'amount': row.amount
			})

		try:
			mi.save(ignore_permissions=True)
			frappe.flags.warehouse_account_map = None
			# mi.update_stock_ledger()
			mi.submit()
			self.db_set('issue_ref',mi.name)
			self.issue_ref = mi.name
		except Exception as e:
			raise e

	# def cancel_repack_entry(self):
	# 	se = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
	# 	se.flags.ignore_permissions = True
	# 	try:
	# 		se.cancel()
	# 	except Exception as e:
	# 		raise e
	# 	se.db_set('reference_doctype','')
	# 	se.db_set('reference_docname','')


	# def cancel_material_issue(self):
	# 	mi = frappe.get_doc("Stock Entry",{'reference_doctype': self.doctype,'reference_docname':self.name})
	# 	mi.flags.ignore_permissions = True
	# 	try:
	# 		mi.cancel()
	# 	except Exception as e:
	# 		raise e
	# 	mi.db_set('reference_doctype','')
	# 	mi.db_set('reference_docname','')