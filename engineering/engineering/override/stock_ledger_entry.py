from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, formatdate

def on_submit(self):
    self.check_stock_frozen_date()
    self.actual_amt_check()
    # Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
    if not self.get("via_landed_cost_voucher") and not self.get('change_rate'):
    # Finbyz Changes End
        from erpnext.stock.doctype.serial_no.serial_no import process_serial_no
        process_serial_no(self)
