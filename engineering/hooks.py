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
	"BOM":"public/js/doctype_js/bom.js",
	"Work Order": "public/js/doctype_js/work_order.js",
	"Stock Entry": "public/js/doctype_js/stock_entry.js",
	"Company": "public/js/doctype_js/company.js",
	"Batch": "public/js/doctype_js/batch.js",
	"Serial No": "public/js/doctype_js/serial_no.js",
	# "Bank Statement Transaction Entry":"public/js/doctype_js/bank_statement_transaction_entry.js",
	"Salary Slip": "public/js/doctype_js/salary_slip.js",
}

doc_events = {
	"Serial No":{
		"validate":"engineering.engineering.doc_events.serial_no.validate",
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
		"validate": "engineering.controllers.item_validation.validate_item_authority",
		"on_submit": "engineering.engineering.doc_events.sales_order.on_submit",
		"on_cancel": "engineering.engineering.doc_events.sales_order.on_cancel",
		"on_trash": "engineering.engineering.doc_events.sales_order.on_trash",
	},
	"Delivery Note": {
		"before_validate": "engineering.engineering.doc_events.delivery_note.before_validate",
		"validate": [
			"engineering.controllers.item_validation.validate_item_authority",
			"engineering.engineering.doc_events.delivery_note.validate",
		],
		"before_naming": "engineering.api.before_naming",
		"before_cancel":"engineering.engineering.doc_events.delivery_note.before_cancel",
		"on_cancel": "engineering.engineering.doc_events.delivery_note.on_cancel",
		"before_submit": "engineering.engineering.doc_events.delivery_note.before_submit",
		"on_submit": "engineering.engineering.doc_events.delivery_note.on_submit",
		"on_trash": "engineering.engineering.doc_events.delivery_note.on_trash",
	},
	"Purchase Order": {
		"before_naming": "engineering.api.before_naming",
		"before_validate": "engineering.engineering.doc_events.purchase_order.before_validate",
		"validate": "engineering.controllers.item_validation.validate_item_authority",
		"on_submit": "engineering.engineering.doc_events.purchase_order.on_submit",
		"on_cancel": "engineering.engineering.doc_events.purchase_order.on_cancel",
		"on_trash": "engineering.engineering.doc_events.purchase_order.on_trash",
	},
	"Purchase Invoice": {
		"before_naming": ["engineering.engineering.doc_events.purchase_invoice.before_naming", "engineering.api.before_naming"],
		"before_validate":"engineering.engineering.doc_events.purchase_invoice.before_validate",
		"validate": "engineering.controllers.item_validation.validate_item_authority",
		"on_submit": "engineering.engineering.doc_events.purchase_invoice.on_submit",
		"on_cancel": "engineering.engineering.doc_events.purchase_invoice.on_cancel",
		"on_trash": "engineering.engineering.doc_events.purchase_invoice.on_trash",
	},
	"Sales Invoice": {
		"before_naming": [
			"engineering.engineering.doc_events.sales_invoice.before_naming",
			"engineering.api.before_naming",
		],
		"before_validate": "engineering.engineering.doc_events.sales_invoice.before_validate",
		"validate": [
			"engineering.engineering.doc_events.sales_invoice.validate",
			"engineering.controllers.item_validation.validate_item_authority"
		],
		"on_submit": "engineering.engineering.doc_events.sales_invoice.on_submit",
		"on_cancel": "engineering.engineering.doc_events.sales_invoice.on_cancel",
		"on_trash": "engineering.engineering.doc_events.sales_invoice.on_trash",
	},
	"Payment Entry": {
		"before_naming": "engineering.api.before_naming",
		"validate": "engineering.engineering.doc_events.payment_entry.validate",
		"on_submit": "engineering.engineering.doc_events.payment_entry.on_submit",
		"on_update_after_submit": "engineering.engineering.doc_events.payment_entry.on_update_after_submit",
		"on_cancel": "engineering.engineering.doc_events.payment_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.payment_entry.on_trash",
	},
	"Customer": {
		"onload": "engineering.engineering.doc_events.customer.onload",
	},
	"Company": {
		"on_update": "engineering.engineering.doc_events.company.on_update",
	},
	"Purchase Receipt": {
		"before_naming": "engineering.api.before_naming",
		"before_validate": "engineering.engineering.doc_events.purchase_receipt.before_validate",
		"validate": "engineering.controllers.item_validation.validate_item_authority",
		"before_submit": "engineering.engineering.doc_events.purchase_receipt.before_submit",
		"before_cancel":"engineering.engineering.doc_events.purchase_receipt.before_cancel",
	},
	"Journal Entry": {
		"before_naming": "engineering.api.before_naming",	
		"on_submit": "engineering.engineering.doc_events.journal_entry.on_submit",
		"on_cancel": "engineering.engineering.doc_events.journal_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.journal_entry.on_trash",
	},
	"Stock Entry": {
		"before_validate": "engineering.engineering.doc_events.stock_entry.before_validate",
		"validate": [
			"engineering.controllers.item_validation.validate_item_authority",
			"engineering.engineering.doc_events.stock_entry.validate",
		],
		"on_submit": "engineering.engineering.doc_events.stock_entry.on_submit",
		"before_cancel": "engineering.engineering.doc_events.stock_entry.before_cancel",
		"on_cancel": "engineering.engineering.doc_events.stock_entry.on_cancel",
		"on_trash": "engineering.engineering.doc_events.stock_entry.on_trash",
	},
	"Fiscal Year": {
		'before_save': 'engineering.engineering.doc_events.fiscal_year.before_save'
	},
	"BOM":{
		"validate":"engineering.engineering.doc_events.bom.validate"
	},
	"Work Order": {
		'validate': 'engineering.engineering.doc_events.work_order.validate'
	},
	"Stock Ledger Entry": {
		'before_submit': 'engineering.engineering.doc_events.stock_ledger_entry.before_submit'
	},
	"Salary Slip":{
		'validate': 'engineering.engineering.doc_events.salary_slip.validate'
	},
	("Sales Invoice", "Purchase Invoice", "Payment Request", "Payment Entry", "Journal Entry", "Material Request", "Purchase Order", "Work Order", "Production Plan", "Stock Entry", "Quotation", "Sales Order", "Delivery Note", "Purchase Receipt", "Packing Slip"): {
		"before_naming": "engineering.api.docs_before_naming",
	},
}

override_doctype_dashboards = {
	"Sales Order": "engineering.engineering.dashboard.sales_order.get_data",
	"Work Order": "engineering.engineering.dashboard.work_order.get_data",
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
	"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_update_cost": "engineering.engineering.doc_events.bom.enqueue_update_cost",
}


# fixtures = ['Custom Field']

# Naming Series Override
from erpnext.setup.doctype.naming_series.naming_series import NamingSeries
from engineering.override_default_class_method import get_transactions
NamingSeries.get_transactions = get_transactions

# # override default class method

from erpnext.stock.stock_ledger import update_entries_after
from engineering.engineering.override.stock_ledger import raise_exceptions, set_actual_qty
update_entries_after.raise_exceptions = raise_exceptions


from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from engineering.engineering.doc_events.stock_entry import get_items as my_get_items, set_serial_nos
StockEntry.set_actual_qty = set_actual_qty
StockEntry.get_items =  my_get_items
StockEntry.set_serial_nos =  set_serial_nos


from erpnext.stock.doctype.serial_no.serial_no import SerialNo
from engineering.engineering.override.serial_no import validate_warehouse, process_serial_no
SerialNo.validate_warehouse = validate_warehouse
SerialNo.process_serial_no = process_serial_no


from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals
from engineering.engineering.override.taxes_and_totals import get_current_tax_amount, determine_exclusive_rate, calculate_taxes
calculate_taxes_and_totals.get_current_tax_amount = get_current_tax_amount
calculate_taxes_and_totals.determine_exclusive_rate= determine_exclusive_rate
calculate_taxes_and_totals.calculate_taxes = calculate_taxes


# Opening Invoice Item Creation tool override
from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import OpeningInvoiceCreationTool
from engineering.engineering.override.opening_invoice_creation_tool import get_invoice_dict, make_invoices
OpeningInvoiceCreationTool.get_invoice_dict = get_invoice_dict
OpeningInvoiceCreationTool.make_invoices = make_invoices


# Override for Change rate of purchase_receipt from purchase_invoice
from erpnext.controllers.buying_controller import BuyingController
from engineering.engineering.override.buying_controller import update_stock_ledger
BuyingController.update_stock_ledger = update_stock_ledger


from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import StockLedgerEntry
from engineering.engineering.override.stock_ledger_entry import on_submit
StockLedgerEntry.on_submit = on_submit


from erpnext.stock.doctype.bin.bin import Bin
from engineering.engineering.override.bin import update_stock
Bin.update_stock = update_stock


from erpnext.stock import stock_ledger
from engineering.engineering.override.stock_ledger import make_sl_entries
stock_ledger.make_sl_entries = make_sl_entries


# Override get rate function for company wise rate
from erpnext.manufacturing.doctype.bom.bom import BOM
from engineering.engineering.doc_events.bom import get_rm_rate
BOM.get_rm_rate = get_rm_rate



# from erpnext.accounts.doctype.bank_statement_transaction_entry.bank_statement_transaction_entry import BankStatementTransactionEntry
# from engineering.engineering.doc_events.bank_statement_transaction_entry import create_payment_entry, match_invoice_to_payment, populate_matching_vouchers
# BankStatementTransactionEntry.create_payment_entry = create_payment_entry
# BankStatementTransactionEntry.match_invoice_to_payment = match_invoice_to_payment
# BankStatementTransactionEntry.populate_matching_vouchers = populate_matching_vouchers


# from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
# from engineering.engineering.doc_events.sales_invoice import validate_serial_against_sales_invoice
# SalesInvoice.validate_serial_against_sales_invoice = validate_serial_against_sales_invoice

# from engineering.override_default_class_method import search_serial_or_batch_or_barcode_number
# # erpnext.selling.page.point_of_sale.point_of_sale.search_serial_or_batch_or_barcode_number = search_serial_or_batch_or_barcode_number