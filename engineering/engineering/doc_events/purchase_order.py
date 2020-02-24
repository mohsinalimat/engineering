# -*- coding: utf-8 -*-
# Copyright (c) 2020, Finbyz Tech Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import get_url_to_form
from engineering.api import make_inter_company_transaction


def on_submit(self, method):
	create_sales_order(self)

def on_cancel(self, method):
	cancel_sales_order(self)

def on_trash(self, method):
	delete_sales_order(self)

def create_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")

	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.company)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]
		
		if self.supplier in inter_company_list:
			field_map = {
				"schedule_date": "delivery_date",
				"name": "po_no",
				"transaction_date": "po_date",
			}
			child_field_map = {
				"name": "purchase_order_item",
			}
			so = make_inter_company_transaction(self, "Purchase Order", "Sales Order", "purchase_order", field_map = field_map, child_field_map = child_field_map)
			try:
				so.save(ignore_permissions = True)
				so.submit()
				
				frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_no', so.name)
				frappe.db.set_value('Purchase Order', self.name, 'inter_company_order_reference', so.name)
				frappe.db.set_value('Purchase Order', self.name, 'sales_order', so.name)
				frappe.db.set_value('Purchase Order', self.name, 'order_confirmation_date', so.transaction_date)

				frappe.db.set_value("Sales Order", so.name, 'inter_company_order_reference', self.name)
				frappe.db.set_value("Sales Order", so.name, 'purchase_order', self.name)

				url = get_url_to_form("Sales Order", so.name)
				frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=so.name)), title="Sales Order Created", indicator="green")
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
			else:
				frappe.db.commit()

def cancel_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		if check_inter_company_transaction == 1:
			company = frappe.get_doc("Company", self.company)
			inter_company_list = [item.company for item in company.allowed_to_transact_with]
			if self.supplier in inter_company_list:
				if self.sales_order:
					try:
						so = frappe.get_doc("Sales Order", self.sales_order)
						so.flags.ignore_permissions = True
						so.cancel()

						url = get_url_to_form("Sales Order", so.name)
						frappe.msgprint(_("Sales Order <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=so.name)), title="Sales Order Cancelled", indicator="red")
					except:
						pass

def delete_sales_order(self):
	check_inter_company_transaction = frappe.get_value("Company", self.company, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		if check_inter_company_transaction == 1:
			company = frappe.get_doc("Company", self.company)
			inter_company_list = [item.company for item in company.allowed_to_transact_with]
			
			if self.supplier in inter_company_list:
				try:
					frappe.db.set_value("Purchase Order", self.name, 'inter_company_order_reference', '')
					frappe.db.set_value("Purchase Order", self.name, 'sales_order', '')
					frappe.db.set_value("Purchase Order", self.name, 'order_confirmation_no', '')

					frappe.db.set_value("Sales Order", self.sales_order, 'inter_company_order_reference', '')
					frappe.db.set_value("Sales Order", self.sales_order, 'purchase_order', '')
					frappe.db.set_value("Sales Order", self.sales_order, 'po_no', '')
					
					frappe.delete_doc("Sales Order", self.sales_order, force = 1, ignore_permissions=True)
					frappe.msgprint(_("Sales Order <b>{name}</b> has been deleted!".format(name=self.sales_order)), title="Sales Order Deleted", indicator="red")
				except Exception as e:
					frappe.db.rollback()
					frappe.throw(e)
				else:
					frappe.db.commit()
