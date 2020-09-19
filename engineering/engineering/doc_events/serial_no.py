# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cstr, cint
def before_save(self, method):
	# # for item in self.transaction_details:
	# # 	frappe.delete_doc("Serial Transaction Details", item.name, ignore_permission = True)
	pass
	# self.transaction_details = []
	# serial_no = self.name
	
	# sle_data = frappe.db.sql("""
	# 	SELECT voucher_type, voucher_no,
	# 		voucher_type, voucher_no, posting_date, posting_time, incoming_rate, actual_qty, serial_no, company
	# 	FROM
	# 		`tabStock Ledger Entry`
	# 	WHERE
	# 		item_code=%s AND ifnull(is_cancelled, 'No')='No'
	# 		AND (serial_no = %s
	# 			OR serial_no like %s
	# 			OR serial_no like %s
	# 			OR serial_no like %s
	# 		)
	# 	ORDER BY
	# 		posting_date desc, posting_time desc, creation desc""",
	# 	(self.item_code,
	# 		serial_no, serial_no+'\n%', '%\n'+serial_no, '%\n'+serial_no+'\n%'), as_dict=1)
	
	# for sle in sle_data:
	# 	row_list = [item.company for item in self.transaction_details]

	# 	if sle.company in row_list:
	# 		row = self.transaction_details[row_list.index(sle.company)]
	# 	else:
	# 		row = self.append('transaction_details', {})

	# 	if serial_no.upper() in get_serial_nos(sle.serial_no):
	# 		if cint(sle.actual_qty) > 0:
	# 			row.purchase_document_type = sle.voucher_type
	# 			row.purchase_document_no = sle.voucher_no
	# 			row.purchase_date = sle.posting_date
	# 			row.purchase_time = sle.posting_time
	# 			row.purchase_rate = sle.incoming_rate

	# 			if self.supplier:
	# 				row.supplier = self.supplier

	# 		else:
	# 			row.delivery_document_type = sle.voucher_type
	# 			row.delivery_document_no = sle.voucher_no
	# 			row.delivery_date = sle.posting_date
	# 			row.delivery_time = sle.posting_time
				
	# 			if self.customer:
	# 				row.customer = self.customer
				
	# 		row.company = sle.company
	# 		row.is_cancelled = sle.is_cancelled

def on_save(self, method):
	# if not self.transaction_details:
	# 	self.db_set("item_code", '')
	# 	self.db_set("warehouse", '')
	# 	self.db_set("company", '')
	pass

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]


def before_validate(self, method):
	pass

# def validate_item(self):
# 	"""
# 		Validate whether serial no is required for this item
# 	"""
# 	if self.item_code:
# 		item = frappe.get_cached_doc("Item", self.item_code)
# 		if item.has_serial_no!=1:
# 			frappe.throw(_("Item {0} is not setup for Serial Nos. Check Item master").format(self.item_code))

# 		self.item_group = item.item_group
# 		self.description = item.description
# 		self.item_name = item.item_name
# 		self.brand = item.brand
# 		self.warranty_period = item.warranty_period
