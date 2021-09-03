import frappe
from frappe import _, ValidationError

import frappe
import erpnext
import json
from frappe import _, ValidationError
from frappe.utils import flt, cint
from erpnext.stock.get_item_details import get_reserved_qty_for_so
from erpnext.stock.doctype.serial_no.serial_no import (get_item_details, update_serial_nos, get_serial_nos,
	validate_material_transfer_entry, has_serial_no_exists,
	allow_serial_nos_with_different_item,check_serial_no_validity_on_cancel,SerialNoCannotCannotChangeError)
class SerialNoRequiredError(ValidationError): pass
class SerialNoNotRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoDuplicateError(ValidationError): pass



# SerialNo class method override
def validate_warehouse(self):
	if not self.get("__islocal"):
		item_code, warehouse = frappe.db.get_value("Serial No",
			self.name, ["item_code", "warehouse"])

		# FinByz Changes Start
		if item_code:	
			if not self.via_stock_ledger and item_code != self.item_code and self.status != "Inactive":
				frappe.throw(_(f"Item Code cannot be changed for Serial No. {self.name}"),
					SerialNoCannotCannotChangeError)
		if warehouse:
			if not self.via_stock_ledger and warehouse != self.warehouse:
				frappe.throw(_(f"Warehouse cannot be changed for Serial No. {self.name}"),
					SerialNoCannotCannotChangeError)
		# FinByz Changes End

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
	elif not sle.is_cancelled:
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
						"delivery_document_no", "delivery_document_type", "warehouse", "purchase_document_type",
						"purchase_document_no", "company", "status"], as_dict=1)
					#finbyz changes Start
					if sr.item_code:
						#finbyz Changes End
						if sr.item_code!=sle.item_code:
							if not allow_serial_nos_with_different_item(serial_no, sle):
								frappe.throw(_("Serial No {0} does not belong to Item {1}").format(serial_no,
									sle.item_code), SerialNoItemError)

					if cint(sle.actual_qty) > 0 and has_serial_no_exists(sr, sle):
						doc_name = frappe.bold(get_link_to_form(sr.purchase_document_type, sr.purchase_document_no))
						frappe.throw(_("Serial No {0} has already been received in the {1} #{2}")
							.format(frappe.bold(serial_no), sr.purchase_document_type, doc_name), SerialNoDuplicateError)

					if (sr.delivery_document_no and sle.voucher_type not in ['Stock Entry', 'Stock Reconciliation']
						and sle.voucher_type == sr.delivery_document_type):
						return_against = frappe.db.get_value(sle.voucher_type, sle.voucher_no, 'return_against')
						if return_against and return_against != sr.delivery_document_no:
							frappe.throw(_("Serial no {0} has been already returned").format(sr.name))

					if cint(sle.actual_qty) < 0:
						if sr.warehouse!=sle.warehouse:
							frappe.throw(_("Serial No {0} does not belong to Warehouse {1}").format(serial_no,
								sle.warehouse), SerialNoWarehouseError)

						if not sr.purchase_document_no:
							frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)

						if sle.voucher_type in ("Delivery Note", "Sales Invoice"):

							if sr.batch_no and sr.batch_no != sle.batch_no:
								frappe.throw(_("Serial No {0} does not belong to Batch {1}").format(serial_no,
									sle.batch_no), SerialNoBatchError)

							if not sle.is_cancelled and not sr.warehouse:
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
		# SLE is being cancelled and has serial nos
		for serial_no in serial_nos:
			check_serial_no_validity_on_cancel(serial_no, sle)	

@frappe.whitelist()
def auto_fetch_serial_number(qty, item_code, warehouse, posting_date=None,batch_nos=None):
	import json
	filters = {
		"item_code": item_code,
		"warehouse": warehouse,
		"delivery_document_no": "",
		"purchase_document_no":('!=',''),
		"purchase_date":('<=',posting_date)
	}
	if batch_nos: filters["batch_no"] = ["in", json.loads(batch_nos)]

	serial_numbers = frappe.get_list("Serial No", filters=filters, limit=qty, order_by="creation")
	return [item['name'] for item in serial_numbers]