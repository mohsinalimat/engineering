# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "engineering"
app_title = "Engineering"
app_publisher = "FinByz"
app_description = "Engineering App"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@finbyz.tech"
app_license = "MIT"


from erpnext.setup.doctype.naming_series.naming_series import NamingSeries
from engineering.override_default_class_method import get_transactions
NamingSeries.get_transactions = get_transactions

# include js, css files in header of desk.html
app_include_css = "/assets/css/restrict_button.css"
app_include_js = "/assets/js/restrict_access.js"

doctype_js = {
	"Sales Order": "public/js/doctype_js/sales_order.js",
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Payment Entry": "public/js/doctype_js/payment_entry.js",
	"Journal Entry": "public/js/doctype_js/journal_entry.js",
	"Item": "public/js/doctype_js/item.js",
	"Work Order": "public/js/doctype_js/work_order.js",
	"Stock Entry": "public/js/doctype_js/stock_entry.js",
}

doc_events = {
	"Item Packing":{
		"before_naming": "engineering.api.before_naming",
	},
	"Account": {
		"validate": "engineering.engineering.doc_events.account.validate",
		"on_trash": "engineering.engineering.doc_events.account.on_trash",
	},
	"Cost Center": {
		"validate": "engineering.engineering.doc_events.cost_center.validate",
		"after_rename": "engineering.engineering.doc_events.cost_center.after_rename",
		"on_trash": "engineering.engineering.doc_events.cost_center.on_trash",
	},
	"Warehouse": {
		"validate": "engineering.engineering.doc_events.warehouse.validate",
		"after_rename": "engineering.engineering.doc_events.warehouse.after_rename",
		"on_trash": "engineering.engineering.doc_events.warehouse.on_trash",
	},
	"Sales Order": {
		"before_naming": "engineering.api.before_naming",
		"before_validate": "engineering.engineering.doc_events.sales_order.before_validate",
		"on_submit": "engineering.engineering.doc_events.sales_order.on_submit",
		"on_cancel": "engineering.engineering.doc_events.sales_order.on_cancel",
		"on_trash": "engineering.engineering.doc_events.sales_order.on_trash",
	},
	"Delivery Note": {
		"before_validate": "engineering.engineering.doc_events.delivery_note.before_validate",
		"before_naming": "engineering.api.before_naming",
		"on_cancel": "engineering.engineering.doc_events.delivery_note.on_cancel",
		"on_submit": "engineering.engineering.doc_events.delivery_note.on_submit",
		"before_submit": "engineering.engineering.doc_events.delivery_note.before_submit",
		"on_trash": "engineering.engineering.doc_events.delivery_note.on_trash",
	},
	"Purchase Order": {
		"before_validate": "engineering.engineering.doc_events.purchase_order.before_validate",
		"on_submit": "engineering.engineering.doc_events.purchase_order.on_submit",
		"before_naming": "engineering.api.before_naming",
		"on_cancel": "engineering.engineering.doc_events.purchase_order.on_cancel",
		"on_trash": "engineering.engineering.doc_events.purchase_order.on_trash",
	},
	"Purchase Invoice": {
		"before_validate": "engineering.engineering.doc_events.purchase_invoice.before_validate",
		"on_submit": "engineering.engineering.doc_events.purchase_invoice.on_submit",
		"on_cancel": "engineering.engineering.doc_events.purchase_invoice.on_cancel",
		"on_trash": "engineering.engineering.doc_events.purchase_invoice.on_trash",
		"before_naming": "engineering.api.before_naming",
	},
	"Sales Invoice": {
		"before_validate": "engineering.engineering.doc_events.sales_invoice.before_validate",
		"before_naming": "engineering.api.before_naming",
		"validate": "engineering.engineering.doc_events.sales_invoice.validate",
		"on_submit": "engineering.engineering.doc_events.sales_invoice.on_submit",
		"on_cancel": "engineering.engineering.doc_events.sales_invoice.on_cancel",
		"on_trash": "engineering.engineering.doc_events.sales_invoice.on_trash",
	},
	"Payment Entry": {
		"before_naming": "engineering.api.before_naming",
		"on_submit": "engineering.engineering.doc_events.payment_entry.on_submit",
		"on_cancel": "engineering.engineering.doc_events.payment_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.payment_entry.on_trash",
	},
	"Customer": {
		"onload": "engineering.engineering.doc_events.customer.onload",
	},
	"Company": {
		"on_update": "engineering.engineering.doc_events.company.on_update",
	},
	"Serial No": {
		"before_save": "engineering.engineering.doc_events.serial_no.before_save",
		"before_validate": "engineering.engineering.doc_events.serial_no.before_validate",
		"on_update": "engineering.engineering.doc_events.serial_no.on_save",
	},
	"Purchase Receipt": {
		"before_naming": "engineering.api.before_naming",
		"before_validate": "engineering.engineering.doc_events.purchase_receipt.before_validate",
	},
	"Journal Entry": {
		"on_submit": "engineering.engineering.doc_events.journal_entry.on_submit",
		"on_cancel": "engineering.engineering.doc_events.journal_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.journal_entry.on_trash",
		"before_naming": "engineering.api.before_naming",	
	},
	"Stock Entry": {
		"on_submit": "engineering.engineering.doc_events.stock_entry.on_submit",
		"on_cancel": "engineering.engineering.doc_events.stock_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.stock_entry.on_trash",
		"before_validate": "engineering.engineering.doc_events.stock_entry.before_validate",
	},
	("Sales Invoice", "Purchase Invoice", "Payment Request", "Payment Entry", "Journal Entry", "Material Request", "Purchase Order", "Work Order", "Production Plan", "Stock Entry", "Quotation", "Sales Order", "Delivery Note", "Purchase Receipt", "Packing Slip"): {
		"before_naming": "engineering.api.docs_before_naming",
	}
}

override_doctype_dashboards = {
	"Sales Order": "engineering.engineering.dashboard.sales_order.get_data",
}

override_whitelisted_methods = {
	"frappe.core.page.permission_manager.permission_manager.get_roles_and_doctypes": "engineering.permission.get_roles_and_doctypes",
	"frappe.core.page.permission_manager.permission_manager.get_permissions": "engineering.permission.get_permissions",
	"frappe.core.page.permission_manager.permission_manager.add": "engineering.permission.add",
	"frappe.core.page.permission_manager.permission_manager.update": "engineering.permission.update",
	"frappe.core.page.permission_manager.permission_manager.remove": "engineering.permission.remove",
	"frappe.core.page.permission_manager.permission_manager.reset": "engineering.permission.reset",
	"frappe.core.page.permission_manager.permission_manager.get_users_with_role": "engineering.permission.get_users_with_role",
	"frappe.core.page.permission_manager.permission_manager.get_standard_permissions": "engineering.permission.get_standard_permissions",
	"frappe.desk.notifications.get_open_count": "engineering.api.get_open_count",
}


# fixtures = ['Custom Field']

from erpnext.stock.stock_ledger import update_entries_after
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.serial_no.serial_no import SerialNo
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

from engineering.override_default_class_method import search_serial_or_batch_or_barcode_number

from engineering.engineering.override.stock_ledger import raise_exceptions, set_actual_qty
from engineering.engineering.override.serial_no import validate_warehouse
from engineering.engineering.override.taxes_and_totals import get_current_tax_amount, determine_exclusive_rate, calculate_taxes

from engineering.engineering.doc_events.stock_entry import get_items as my_get_items
# erpnext.selling.page.point_of_sale.point_of_sale.search_serial_or_batch_or_barcode_number = search_serial_or_batch_or_barcode_number
# override default class method
update_entries_after.raise_exceptions = raise_exceptions
StockEntry.set_actual_qty = set_actual_qty
StockEntry.get_items =  my_get_items
SerialNo.validate_warehouse = validate_warehouse
calculate_taxes_and_totals.get_current_tax_amount = get_current_tax_amount
calculate_taxes_and_totals.determine_exclusive_rate= determine_exclusive_rate
calculate_taxes_and_totals.calculate_taxes = calculate_taxes
