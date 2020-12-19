from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	return [
		{
			"label": _("Buying"),
			"items": [
				{
					"type": "doctype",
					"name": "Material Request",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Purchase Order",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Request for Quotation",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "report",
					"name": "Purchase Register Engineering",
					"doctype": "Sales Invoice",
					"is_query_report": True
				},
			]
		},
		{
			"label": _("Production"),
			"items": [
				{
					"type": "doctype",
					"name": "Work Order",
					"description": _(""),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Item Packing",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Stock Entry",
					"description": _(""),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Stock Transactions"),
			"items": [
				{
					"type": "doctype",
					"name": "Stock Entry",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Delivery Note",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Purchase Receipt",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Work Return",
					"description": _(""),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Stock Report"),
			"items": [
				{
					"type": "report",
					"name": "Item Groupwise Stock Balance",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Stock Balance Engineering",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Stock Ledger Engineering",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Serial No & Batch"),
			"items": [
				{
					"type": "report",
					"name": "Serial no wise stock movement",
					"is_query_report": False,
				},
				{
					"type": "doctype",
					"name": "Serial No",
					"description": _(""),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Batch",
					"description": _(""),
					"onboard": 1,
				},
			]
		},
		{
			"label": _("Selling"),
			"items": [
				{
					"type": "doctype",
					"name": "Customer",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Quotation",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Sales Order",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "report",
					"name": "Sales Register Engineering",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Item And Pricing"),
			"items": [
				{
					"type": "doctype",
					"name": "Item Price",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Price List",
					"description": _(""),
                    "onboard": 1,
				},
			]
		},
		{
			"label": _("Account Receivable"),
			"items": [
				{
					"type": "doctype",
					"name": "Sales Invoice",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Customer",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payment Request",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "report",
					"name": "Sales Register Engineering",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Accounts Receivable Engineering",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Accounts Receivable Engineering Summary",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Account Payable"),
			"items": [
				{
					"type": "doctype",
					"name": "Purchase Invoice",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Supplier",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payment Entry",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "report",
					"name": "Purchase Register Engineering",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Accounts Payable Engineering",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Accounts Payable Engineering Summary",
					"is_query_report": True,
				},
			]


		},
		{
			"label": _("General Ledger"),
			"items": [
				{
					"type": "doctype",
					"name": "Journal Entry",
					"description": _(""),
                    "onboard": 1,
				},
				{
					"type": "report",
					"name": "Daybook Engineering",
					"is_query_report": True,
				},
			]
		},
		{
			"label": _("Advance Reports"),
			"items": [
				{
					"type": "report",
					"name": "Stock Ageing",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Sales Analytics",
					"is_query_report": True,
				},
				{
					"type": "report",
					"name": "Purchase Analytics",
					"is_query_report": True,
				},
			]
		},
	]