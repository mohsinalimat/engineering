import frappe
from frappe import _
from frappe.utils import cstr

def on_cancel(self, method):
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()

def on_submit(self, method):
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]