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

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = ["/assets/engineering/css/engineering.css"]
# app_include_js = "/assets/engineering/js/engineering.js"

# include js, css files in header of web template
# web_include_css = "/assets/engineering/css/engineering.css"
# web_include_js = "/assets/engineering/js/engineering.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "engineering.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "engineering.install.before_install"
# after_install = "engineering.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "engineering.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"engineering.tasks.all"
# 	],
# 	"daily": [
# 		"engineering.tasks.daily"
# 	],
# 	"hourly": [
# 		"engineering.tasks.hourly"
# 	],
# 	"weekly": [
# 		"engineering.tasks.weekly"
# 	]
# 	"monthly": [
# 		"engineering.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "engineering.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "engineering.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "engineering.task.get_dashboard_data"
# }

doctype_js = {
	"Sales Order": "public/js/doctype_js/sales_order.js",
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Payment Entry": "public/js/doctype_js/payment_entry.js",
}

doc_events = {
	"Sales Order": {
		"before_naming": "engineering.api.before_naming",
	},
	"Purchase Invoice": {
		"on_submit": "engineering.engineering.doc_events.purchase_invoice.on_submit",
		"on_cancel": "engineering.engineering.doc_events.purchase_invoice.on_cancel",
		"on_trash": "engineering.engineering.doc_events.purchase_invoice.on_trash",
		"before_naming": "engineering.api.before_naming",
	},
	"Delivery Note": {
		"before_naming": "engineering.api.before_naming",
		"on_submit": "engineering.engineering.doc_events.delivery_note.on_submit",
	},
	"Sales Invoice": {
		"before_naming": "engineering.api.before_naming",
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
	("Sales Invoice", "Purchase Invoice", "Payment Request", "Payment Entry", "Journal Entry", "Material Request", "Purchase Order", "Work Order", "Production Plan", "Stock Entry", "Quotation", "Sales Order", "Delivery Note", "Purchase Receipt", "Packing Slip"): {
		"before_naming": "engineering.api.docs_before_naming",
	}
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


fixtures = ['Custom Field']	
