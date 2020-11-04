# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint,cstr


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