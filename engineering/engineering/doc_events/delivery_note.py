# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import get_url_to_form

from engineering.api import make_inter_company_transaction


def on_cancel(self, method):
	cancel_purchase_received(self)

def cancel_purchase_received(self):
	try:
		check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
	except:
		check_inter_company_transaction = None
	
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]
		
		if self.company in inter_company_list:
				
			pi = frappe.get_doc("Purchase Receipt", self.inter_company_receipt_reference)
			pi.flags.ignore_permissions = True
			try:
				pi.cancel()

				url = get_url_to_form("Purchase Receipt", pi.name)
				frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=pr.name)), title="Purchase Receipt Cancelled", indicator="red")
			except:
				pass

def on_submit(self, method):
	"""Custom On Submit Fuction"""

	create_purchase_receipt(self)
	change_delivery_authority(self.name)

def on_trash(self, method):
	""" Custom On Trash Function """

	delete_purchase_receipt(self)

def delete_purchase_receipt(self):
	check_inter_company_transaction = None
	if frappe.db.exists("Company", self.customer, "allow_inter_company_transaction"):
		check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]

		frappe.db.set_value("Delivery Note", self.name, 'inter_company_receipt_reference', '')
		frappe.db.set_value("Purchase Receipt", self.inter_company_receipt_reference, 'inter_company_delivery_reference', '')
		
		frappe.delete_doc("Purchase Receipt", self.inter_company_receipt_reference, force = 1, ignore_permissions=True)
		frappe.msgprint(_("Purchase Receipt {name} has been deleted!".format(name=frappe.bold(self.inter_company_receipt_reference))), title="Purchase Receipt Deleted", indicator="red")

def create_purchase_receipt(self):
	check_inter_company_transaction = None
	if frappe.db.exists("Company", self.customer, "allow_inter_company_transaction"):
		check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]

		if self.company in inter_company_list:
			field_map = {
				"name": "supplier_delivery_note",
			}
			child_field_map = {
				"purchase_order_item": "purchase_order_item",
			}
			pr = make_inter_company_transaction(self, "Delivery Note", "Purchase Receipt", "inter_company_delivery_reference", field_map=field_map, child_field_map = child_field_map)

			pr.save(ignore_permissions = True)
			
			for index, item in enumerate(self.items):
				against_sales_order = self.items[index].against_sales_order
				try:
					purchase_order = frappe.db.get_value("Sales Order", against_sales_order, 'inter_company_order_reference')
				except:
					purchase_order = None
					
				if purchase_order:
					schedule_date = frappe.db.get_value("Purchase Order", purchase_order, 'schedule_date')
					pr.items[index].purchase_order = purchase_order
					pr.items[index].schedule_date = schedule_date
					frappe.db.set_value("Delivery Note Item", self.items[index].name, 'pr_detail', pr.items[index].name)
			
			pr.save(ignore_permissions = True)

			self.db_set('inter_company_receipt_reference', pr.name)
			pr.db_set('inter_company_delivery_reference', self.name)
			pr.db_set('supplier_delivery_note', self.name)

			url = get_url_to_form("Purchase Receipt", pr.name)
			# frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully! Please submit the Purchase Recipient".format(url=url, name=frappe.bold(pr.name))), title="Purchase Receipt Created", indicator="green")

def change_delivery_authority(name):
	"""Function to change authorty of Delivery Note"""

	status = frappe.get_value("Delivery Note", name, "status")
	
	if status == 100.0:
		frappe.db.set_value("Delivery Note",name, "status", "Completed")
	else:
		frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
	
	frappe.db.commit()


@frappe.whitelist()
def create_invoice(source_name, target_doc=None):
	doc = frappe.get_doc('Delivery Note', source_name)

	to_make_invoice_qty_map = {}
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		try:
			alternate_customer = frappe.db.get_value("Company", source.customer, "alternate_company")
		except:
			alternate_customer = None
		
		target.is_pos = 0
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")
		target.expense_account = ""
		target.update_stock = 1

		if alternate_company:
			target.company = alternate_company

		if alternate_customer:
			target.customer = alternate_customer

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been invoiced"))

		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))


	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

		returned_qty = 0
		if returned_qty_map.get(item_row.item_code, 0) > 0:
			returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
			returned_qty_map[item_row.item_code] -= pending_qty

		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		to_make_invoice_qty_map[item_row.name] = pending_qty

		return pending_qty
	
	def update_acoounts(source_doc, target_doc, source_parent):
		target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

		doc = frappe.get_doc("Company", target_company)

		target_doc.income_account = doc.default_income_account
		target_doc.expense_account = doc.default_expense_account
		target_doc.cost_center = doc.cost_center
		abbr = frappe.db.get_value("Company", target_company, 'abbr')
		target_doc.warehouse = "Stores - {}".format(abbr)

	fields = {
		"Delivery Note": {
			"doctype": "Sales Invoice",
			"field_map": {
				"is_return": "is_return"
			},
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Delivery Note Item": {
			"doctype": "Sales Invoice Item",
			"field_map": {
				"item_code": "item_variant",
				"item_series": "item_code",
				"parent": "delivery_docname",
				"name":"delivery_childname",
				"so_detail": "so_childname" ,
				"against_sales_order": "so_docname",
				"serial_no": "serial_no",
				"real_qty": "qty",
				"discounted_rate": "rate",
				"qty": "full_qty",
				"rate":"full_rate",
				"purchase_order_item": "po_ref",
				"pr_detail": "pr_ref",
			},
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse",
				"real_qty",
				"discounted_rate",
				"purchase_order_item",
				"pr_detail",
			],
			"postprocess": update_acoounts,
			"filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}

	doc = get_mapped_doc(
		"Delivery Note",
		source_name,
		fields,
		target_doc,
		set_missing_values
	)

	return doc

def get_invoiced_qty_map(delivery_note):
	"""returns a map: {dn_detail: invoiced_qty}"""

	invoiced_qty_map = {}

	for dn_detail, qty in frappe.db.sql("""select dn_detail, qty from `tabSales Invoice Item`
		where delivery_note=%s and docstatus=1""", delivery_note):
			if not invoiced_qty_map.get(dn_detail):
				invoiced_qty_map[dn_detail] = 0
			invoiced_qty_map[dn_detail] += qty

	return invoiced_qty_map

def get_returned_qty_map(delivery_note):
	"""returns a map: {so_detail: returned_qty}"""

	returned_qty_map = frappe._dict(frappe.db.sql("""select dn_item.item_code, sum(abs(dn_item.qty)) as qty
		from `tabDelivery Note Item` dn_item, `tabDelivery Note` dn
		where dn.name = dn_item.parent
			and dn.docstatus = 1
			and dn.is_return = 1
			and dn.return_against = %s
		group by dn_item.item_code
	""", delivery_note))

	return returned_qty_map

@frappe.whitelist()
def submit_purchase_receipt(pr_number):
	pr = frappe.get_doc("Purchase Receipt", pr_number)
	pr.flags.ignore_permissions = True
	pr.submit()
	frappe.db.commit()

	url = get_url_to_form("Purchase Receipt", pr.name)
	msg = "Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=frappe.bold(pr.name))
	frappe.msgprint(_(msg), title="Purchase Receipt Created", indicator="green")