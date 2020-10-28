# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue, get_jobs

class SubmitorRemoveEntry(Document):
	pass
@frappe.whitelist()
def enqueue_cancel_entry(doc_type,doc_name):
	doc = frappe.get_doc(doc_type,doc_name)
	if doc.docstatus == 2:
		frappe.throw("Entry is Already Cancelled")
	queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
	job = "cancel entry " + doc_name
	if job not in queued_jobs:
		frappe.msgprint("Entry is in Background Jobs Queue. Please Wait for Sometime or Check in error log")
		enqueue(cancel_entry,queue= "long", timeout= 3600, job_name= job, doc_type = doc_type, doc_name = doc_name)

def cancel_entry(doc_type,doc_name):
	doc = frappe.get_doc(doc_type,doc_name)
	doc.cancel()

@frappe.whitelist()
def enqueue_submit_entry(doc_type,doc_name):
	doc = frappe.get_doc(doc_type,doc_name)
	if doc.docstatus !=0:
		frappe.throw("Entry is either Submitted or Cancelled")
	queued_jobs = get_jobs(site=frappe.local.site, key='job_name')[frappe.local.site]
	job = "submit entry " + doc_name
	if job not in queued_jobs:
		frappe.msgprint("Entry is in Background Jobs Queue. Please Wait for Sometime or Check in error log")
		enqueue(submit_entry,queue= "long", timeout= 3600, job_name= job, doc_type = doc_type, doc_name = doc_name)

def submit_entry(doc_type,doc_name):
	doc = frappe.get_doc(doc_type,doc_name)
	doc.submit()
