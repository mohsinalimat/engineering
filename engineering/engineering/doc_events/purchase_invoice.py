import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    # create_main_purchase_invoice(self)
    pass

def on_cancel(self, test):
    """On Cancel Custom Function for Sales Invoice"""
    # cancel_main_purchase_invoice(self)
    pass

def on_trash(self, test):
    # delete_purchase_invoice(self)
    pass

def change_purchase_reciept_authority(name):
    pass
