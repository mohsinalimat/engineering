# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import erpnext
from frappe import _, ValidationError
from frappe.utils import flt, cint
from erpnext.stock.get_item_details import get_reserved_qty_for_so
from erpnext.stock.doctype.serial_no.serial_no import get_item_details, validate_serial_no, update_serial_nos, get_serial_nos, validate_material_transfer_entry, has_duplicate_serial_no, allow_serial_nos_with_different_item
class SerialNoRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoDuplicateError(ValidationError): pass

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

def process_serial_no(sle):
	item_det = get_item_details(sle.item_code)
	validate_serial_no(sle, item_det)
	update_serial_nos(sle, item_det)


def validate_serial_no(sle, item_det):
	serial_nos = get_serial_nos(sle.serial_no) if sle.serial_no else []
	validate_material_transfer_entry(sle)

	if item_det.has_serial_no==0:
		if serial_nos:
			frappe.throw(_("Item {0} is not setup for Serial Nos. Column must be blank").format(sle.item_code),
				SerialNoNotRequiredError)
	elif sle.is_cancelled == "No":
		if serial_nos:
			if cint(sle.actual_qty) != flt(sle.actual_qty):
				frappe.throw(_("Serial No {0} quantity {1} cannot be a fraction").format(sle.item_code, sle.actual_qty))

			if len(serial_nos) and len(serial_nos) != abs(cint(sle.actual_qty)):
				frappe.throw(_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(abs(sle.actual_qty), sle.item_code, len(serial_nos)),
					SerialNoQtyError)

			if len(serial_nos) != len(set(serial_nos)):
				frappe.throw(_("Duplicate Serial No entered for Item {0}").format(sle.item_code), SerialNoDuplicateError)

			
			for serial_no in serial_nos:
			
				if frappe.db.exists("Serial No", serial_no):
					sr = frappe.db.get_value("Serial No", serial_no, ["name", "item_code", "batch_no", "sales_order",
						"delivery_document_no", "delivery_document_type", "warehouse",
						"purchase_document_no", "company"], as_dict=1)
					#finbyz changes Start
					if sr.item_code:
						#finbyz Changes End
						if sr.item_code!=sle.item_code:
							if not allow_serial_nos_with_different_item(serial_no, sle):
								frappe.throw(_("Serial No {0} does not belong to Item {1}").format(serial_no,
									sle.item_code), SerialNoItemError)

					if cint(sle.actual_qty) > 0 and has_duplicate_serial_no(sr, sle):
						frappe.throw(_("Serial No {0} has already been received").format(serial_no),
							SerialNoDuplicateError)

					if (sr.delivery_document_no and sle.voucher_type not in ['Stock Entry', 'Stock Reconciliation']
						and sle.voucher_type == sr.delivery_document_type):
						return_against = frappe.db.get_value(sle.voucher_type, sle.voucher_no, 'return_against')
						if return_against and return_against != sr.delivery_document_no:
							frappe.throw(_("Serial no {0} has been already returned").format(sr.name))

					if cint(sle.actual_qty) < 0:
						if sr.warehouse!=sle.warehouse:
							frappe.throw(_("Serial No {0} does not belong to Warehouse {1}").format(serial_no,
								sle.warehouse), SerialNoWarehouseError)

						if sle.voucher_type in ("Delivery Note", "Sales Invoice"):

							if sr.batch_no and sr.batch_no != sle.batch_no:
								frappe.throw(_("Serial No {0} does not belong to Batch {1}").format(serial_no,
									sle.batch_no), SerialNoBatchError)

							if sle.is_cancelled=="No" and not sr.warehouse:
								frappe.throw(_("Serial No {0} does not belong to any Warehouse")
									.format(serial_no), SerialNoWarehouseError)

							# if Sales Order reference in Serial No validate the Delivery Note or Invoice is against the same
							if sr.sales_order:
								if sle.voucher_type == "Sales Invoice":
									if not frappe.db.exists("Sales Invoice Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "sales_order": sr.sales_order}):
										frappe.throw(_("Cannot deliver Serial No {0} of item {1} as it is reserved \
											to fullfill Sales Order {2}").format(sr.name, sle.item_code, sr.sales_order))
								elif sle.voucher_type == "Delivery Note":
									if not frappe.db.exists("Delivery Note Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code, "against_sales_order": sr.sales_order}):
										invoice = frappe.db.get_value("Delivery Note Item", {"parent": sle.voucher_no,
											"item_code": sle.item_code}, "against_sales_invoice")
										if not invoice or frappe.db.exists("Sales Invoice Item",
											{"parent": invoice, "item_code": sle.item_code,
											"sales_order": sr.sales_order}):
											frappe.throw(_("Cannot deliver Serial No {0} of item {1} as it is reserved to \
												fullfill Sales Order {2}").format(sr.name, sle.item_code, sr.sales_order))
							# if Sales Order reference in Delivery Note or Invoice validate SO reservations for item
							if sle.voucher_type == "Sales Invoice":
								sales_order = frappe.db.get_value("Sales Invoice Item", {"parent": sle.voucher_no,
									"item_code": sle.item_code}, "sales_order")
								if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
									validate_so_serial_no(sr, sales_order)
							elif sle.voucher_type == "Delivery Note":
								sales_order = frappe.get_value("Delivery Note Item", {"parent": sle.voucher_no,
									"item_code": sle.item_code}, "against_sales_order")
								if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
									validate_so_serial_no(sr, sales_order)
								else:
									sales_invoice = frappe.get_value("Delivery Note Item", {"parent": sle.voucher_no,
										"item_code": sle.item_code}, "against_sales_invoice")
									if sales_invoice:
										sales_order = frappe.db.get_value("Sales Invoice Item", {
											"parent": sales_invoice, "item_code": sle.item_code}, "sales_order")
										if sales_order and get_reserved_qty_for_so(sales_order, sle.item_code):
											validate_so_serial_no(sr, sales_order)
				elif cint(sle.actual_qty) < 0:
					# transfer out
					frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)
		elif cint(sle.actual_qty) < 0 or not item_det.serial_no_series:
			frappe.throw(_("Serial Nos Required for Serialized Item {0}").format(sle.item_code),
				SerialNoRequiredError)
	elif serial_nos:
		for serial_no in serial_nos:
			sr = frappe.db.get_value("Serial No", serial_no, ["name", "warehouse"], as_dict=1)
			if sr and cint(sle.actual_qty) < 0 and sr.warehouse != sle.warehouse:
				frappe.throw(_("Cannot cancel {0} {1} because Serial No {2} does not belong to the warehouse {3}")
					.format(sle.voucher_type, sle.voucher_no, serial_no, sle.warehouse))
