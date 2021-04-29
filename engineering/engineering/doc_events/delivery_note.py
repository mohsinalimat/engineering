# Copyright (c) 2020, Finbyz Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, datetime
from frappe import _, ValidationError
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from frappe.utils import get_url_to_form, flt, cint
from frappe.model.utils import get_fetch_values
from erpnext.stock.doctype.serial_no.serial_no import get_item_details, get_serial_nos, validate_so_serial_no
from erpnext.stock.get_item_details import get_reserved_qty_for_so

from engineering.api import make_inter_company_transaction

class SerialNoRequiredError(ValidationError): pass
class SerialNoNotRequiredError(ValidationError): pass
class SerialNoQtyError(ValidationError): pass
class SerialNoWarehouseError(ValidationError): pass
class SerialNoItemError(ValidationError): pass
class SerialNoNotExistsError(ValidationError): pass
class SerialNoDuplicateError(ValidationError): pass

def before_validate(self, method):
	update_discounted_amount(self)
	validate_no_of_boxes(self)
	update_discounted_net_total(self)

def validate(self, method):
	if self._action in ['submit','cancel'] and not self.is_return:
		serial_no_validate(self)

def before_submit(self,method):
	#check_sales_order_item(self)
	pass

def on_submit(self, method):
	validate_rate(self)
	if not self.dont_replicate:
		if not self.is_return:
			create_purchase_receipt(self)
			create_delivery_note(self)
	update_real_delivered_qty(self, "submit")

def before_cancel(self, method):
	cancel_all(self)
def on_cancel(self, method):
	# cancel_all(self)
	update_real_delivered_qty(self, "cancel")

def on_trash(self, method):
	delete_all(self)

def update_discounted_amount(self):
	for item in self.items:
		item.discounted_amount = (item.discounted_rate or 0.0) * (item.real_qty or 0.0)
		item.discounted_net_amount = item.discounted_amount

		# try:
		# 	item.discounted_net_rate = item.discounted_net_amount / item.real_qty
		# except:
		# 	item.discounted_net_rate = 0.0

		if (not item.rate) and (item.so_detail):
			item.rate = frappe.db.get_value("Sales Order Item", item.so_detail, 'rate')
		
		if (not item.discounted_rate) and (item.so_detail):
			item.discounted_rate = frappe.db.get_value("Sales Order Item", item.so_detail, 'discounted_rate')

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	testing_only_tax = 0
	
	for tax in self.taxes:
		if tax.testing_only:
			testing_only_tax += tax.tax_amount
	
	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges - testing_only_tax
	self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total

def cancel_all(self):
	if self.dn_ref:
		doc = frappe.get_doc("Delivery Note", self.dn_ref)
		doc.db_set('pr_ref',None)
		doc.db_set('dn_ref',None)
		self.db_set('dn_ref',None)
		if doc.docstatus == 1:
			doc.cancel()
	if self.inter_company_receipt_reference:
		self.db_set('inter_company_receipt_reference',None)
	if self.pr_ref:
		doc = frappe.get_doc("Purchase Receipt", self.pr_ref)
		doc.db_set('inter_company_delivery_reference', None)
		doc.db_set('supplier_delivery_note', None)
		doc.db_set('dn_ref', None)
		self.db_set('pr_ref',None)
		if doc.docstatus == 1:
			doc.cancel()
		#doc.flags.ignore_links = True
		# if doc.docstatus == 1:
		# 	doc.cancel()

def check_sales_order_item(self):
	auth = frappe.db.get_value("Company", self.company, "authority")
	if auth == "Unauthorized":
		for row in self.items:
			if not row.so_detail:
				frappe.throw("Row {}: Sales Order not found for item {}".format(row.idx,row.item_code))
			

def validate_rate(self):
	for row in self.items:
		if not row.rate:
			frappe.throw("Row {}: Rate should not be Zero for item <b>{}</b>".format(row.idx,row.item_code))
				
def cancel_purchase_received(self):
	if self.pr_ref:
		pr = frappe.get_doc("Purchase Receipt", self.pr_ref)

		if pr.docstatus == 1:
			pr.flags.ignore_permissions = True
			pr.cancel()

		url = get_url_to_form("Purchase Receipt", pr.name)
		frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been cancelled!".format(url=url, name=self.pr_ref)), title="Purchase Receipt Cancelled", indicator="red")

def create_delivery_note(self):
	def get_delivery_note_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.customer
			target.customer = source.final_customer

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges
			if source.items[0].sales_order_item:
				target.selling_price_list = frappe.db.get_value("Sales Order", 
				frappe.db.get_value("Sales Order Item", source.items[0].sales_order_item, 'parent')
				, 'selling_price_list')
			target.set_posting_time = 1
			target.posting_time = source.posting_time + datetime.timedelta(0,10)
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Delivery Note", {'dn_ref': self.amended_from}, "name")
			if source.set_target_warehouse:
				target.set_warehouse = source.set_target_warehouse
			else:
				target.set_warehouse = source.set_warehouse.replace(source_company_abbr, target_company_abbr)

			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.customer, "abbr")

			if source_doc.sales_order_item:
				target_doc.against_sales_order = frappe.db.get_value("Sales Order Item", source_doc.sales_order_item, 'parent')
				target_doc.sales_order_item = source_doc.so_detail

			if source_parent.set_target_warehouse:
				target_doc.warehouse = source_parent.set_target_warehouse
			else:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)
			
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)
			
			if source_doc.sales_order_item:
				target_doc.rate = frappe.db.get_value("Sales Order Item", source_doc.sales_order_item, 'rate')
				target_doc.discounted_rate = frappe.db.get_value("Sales Order Item", source_doc.sales_order_item, 'discounted_rate')

		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.customer, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Delivery Note": {
				"doctype": "Delivery Note",
				"field_map": {
					"name": "supplier_delivery_note",
					"name": "so_ref",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"ignore_pricing_rule": "ignore_pricing_rule",
					"is_return":"is_return",
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
					"customer_name",
					"through_company",
					"shipping_address",
					"shipping_address_name",
					"customer_gstin",
					"contact_person",
					"address_display",
					"billing_gstin",
					"customer_address",
					"company_address_display",
					"company_address",
					"final_customer",
					"set_target_warehouse"
				]
			},
			"Delivery Note Item": {
				"doctype": "Delivery Note Item",
				"field_map": {
					"purchase_order_item": "purchase_order_item",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"sales_order_item": "so_detail",
					"so_detail": "sales_invoice_item",
					"sales_invoice_item": "so_detail",
					"name": "delivery_note_item"
				},
				"field_no_map": [
					"warehouse",
					"cost_center",
					"expense_account",
					"income_account",
				],
				"postprocess": update_items,
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"postprocess": update_taxes,
			}
		}

		doc = get_mapped_doc(
			"Delivery Note",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doc
		
	if self.final_customer:
		dn = get_delivery_note_entry(self.name)
		dn.save(ignore_permissions = True)
		#dn.submit()

		self.db_set("dn_ref", dn.name)
		dn.db_set("through_company", self.company)
		for idx, item in enumerate(self.items):
			item.db_set('delivery_note_item', dn.items[idx].name)
			item.db_set('pr_detail', dn.items[idx].pr_detail)


def update_real_delivered_qty(self, method):
	if method == "submit":
		for item in self.items:
			if item.against_sales_order:
				sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
				delivered_real_qty = item.real_qty + sales_order_item.delivered_real_qty

				sales_order_item.db_set("delivered_real_qty", delivered_real_qty)

	if method == "cancel":
		for item in self.items:
			if item.against_sales_order:
				sales_order_item = frappe.get_doc("Sales Order Item", item.so_detail)
				delivered_real_qty = sales_order_item.delivered_real_qty - item.real_qty

				sales_order_item.db_set("delivered_real_qty", delivered_real_qty)

def delete_all(self):
	dn_ref = [self.dn_ref]
	pr_ref = [self.pr_ref]

	if self.dn_ref:
		doc = frappe.get_doc("Delivery Note", self.dn_ref)

		dn_ref.append(doc.dn_ref)
		pr_ref.append(doc.pr_ref)
	
	for dn in dn_ref:
		if dn:
			frappe.db.set_value("Delivery Note", dn, 'dn_ref', None)
			frappe.db.set_value("Delivery Note", dn, 'pr_ref', None)
			frappe.db.set_value("Delivery Note", dn, 'inter_company_receipt_reference', None)
	
	for pr in pr_ref:
		if pr:
			frappe.db.set_value("Purchase Receipt", pr, 'dn_ref', None)
			frappe.db.set_value("Purchase Receipt", pr, 'inter_company_delivery_reference', None)

	for dn in dn_ref:
		if dn and dn != self.name:
			if frappe.db.exists("Delivery Note", dn):
				frappe.delete_doc("Delivery Note", dn)
	
	for pr in pr_ref:
		if pr:
			if frappe.db.exists("Purchase Receipt", pr):
				frappe.delete_doc("Purchase Receipt", pr)

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
	def get_purchase_receipt_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = source.customer
			target.supplier = source.company

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			if source.taxes_and_charges:
				target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
					target.taxes_and_charges = target_taxes_and_charges

			if self.amended_from:
				name = frappe.db.get_value("Purchase Receipt", {'dn_ref': self.amended_from}, "name")
				target.amended_from = name
			target.set_posting_time = 1
			target.posting_time = source.posting_time + datetime.timedelta(0,5)
			if source.set_target_warehouse:
				target.set_warehouse = source.set_target_warehouse
			else:
				target.set_warehouse = source.set_warehouse.replace(source_company_abbr, target_company_abbr)
			target.run_method("set_missing_values")
			target.run_method("calculate_taxes_and_charges")

		def update_items(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.customer, "abbr")

			if source_parent.set_target_warehouse:
				target_doc.warehouse = source_parent.set_target_warehouse
			else:
				target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		def update_taxes(source_doc, target_doc, source_parent):
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")
			target_company_abbr = frappe.db.get_value("Company", source_parent.customer, "abbr")

			if source_doc.account_head:
				target_doc.account_head = source_doc.account_head.replace(source_company_abbr, target_company_abbr)

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

			target_doc.delivery_note = source_parent.name
		fields = {
			"Delivery Note": {
				"doctype": "Purchase Receipt",
				"field_map": {
					"name": "supplier_delivery_note",
					"selling_price_list": "buying_price_list",
					"posting_date": "posting_date",
					"posting_time": "posting_time",
					"ignore_pricing_rule": "ignore_pricing_rule",
					"shipping_address_name": "shipping_address",
					"customer_gstin": "company_gstin",
					"shipping_address": "shipping_address_display",
					"is_return":"is_return",
				},
				"field_no_map": [
					"taxes_and_charges",
					"series_value",
				]
			},
			"Delivery Note Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"purchase_order_item": "purchase_order_item",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"name":"delivery_note_item"
				},
				"field_no_map": [
					"warehouse",
					"cost_center",
					"expense_account",
					"income_account",
				],
				"postprocess": update_items,
			},
			"Sales Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"postprocess": update_taxes,
			}
		}

		doc = get_mapped_doc(
			"Delivery Note",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doc

	check_inter_company_transaction = None
	if frappe.db.exists("Company", self.customer):
		check_inter_company_transaction = frappe.get_value("Company", self.customer, "allow_inter_company_transaction")
	
	if check_inter_company_transaction:
		company = frappe.get_doc("Company", self.customer)
		inter_company_list = [item.company for item in company.allowed_to_transact_with]

		if self.company in inter_company_list:
			pr = get_purchase_receipt_entry(self.name)
			pr.save(ignore_permissions = True)

			for index, item in enumerate(self.items):
				price_list = self.selling_price_list
				if price_list:
					valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
				else:
					frappe.throw(_("Selected Price List should have buying and selling fields checked."))

				if not valid_price_list:
					frappe.throw(_("Selected Price List should have buying and selling fields checked."))

				against_sales_order = self.items[index].against_sales_order

				purchase_order = None
				if frappe.db.exists("Sales Order", against_sales_order):
					purchase_order = frappe.db.get_value("Sales Order", against_sales_order, 'inter_company_order_reference')

				if purchase_order:
					pr.items[index].schedule_date = frappe.db.get_value("Purchase Order", purchase_order, 'schedule_date')
					pr.items[index].purchase_order = purchase_order
				self.items[index].pr_detail = pr.items[index].name
				# frappe.msgprint(str(pr.items[index].name))
				# frappe.db.set_value("Delivery Note Item", self.items[index].name, 'pr_detail', pr.items[index].name)
			
			pr.save(ignore_permissions = True)

			self.db_set('inter_company_receipt_reference', pr.name)
			self.db_set('pr_ref', pr.name)

			pr.db_set('inter_company_delivery_reference', self.name)
			pr.db_set('supplier_delivery_note', self.name)
			pr.db_set('dn_ref', self.name)

			#pr.submit()

			url = get_url_to_form("Purchase Receipt", pr.name)
			frappe.msgprint(_("Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=frappe.bold(pr.name))), title="Purchase Receipt Created", indicator="green")


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

# All Whitelisted Method

@frappe.whitelist()
def submit_purchase_receipt(pr_number):
	pr = frappe.get_doc("Purchase Receipt", pr_number)
	pr.flags.ignore_permissions = True
	pr.submit()
	frappe.db.commit()

	url = get_url_to_form("Purchase Receipt", pr.name)
	msg = "Purchase Receipt <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=frappe.bold(pr.name))
	frappe.msgprint(_(msg), title="Purchase Receipt Created", indicator="green")

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
		# target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")
		target.expense_account = ""
		target.update_stock = 1

		if alternate_company:
			target.company = alternate_company
		
		if frappe.db.exists("Branch", source.company):
			target.branch = source.company

		if alternate_customer:
			target.customer = alternate_customer

		target.alternate_company = source.company

		if len(target.get("items")) == 0:
			frappe.throw(_("All these items have already been invoiced"))

		target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")
		

		if source.taxes_and_charges:
			target_taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
			if frappe.db.exists("Sales Taxes and Charges Template", target_taxes_and_charges):
				target.taxes_and_charges = target_taxes_and_charges
		target.taxes = source.taxes
		if source.taxes:
			for index, value in enumerate(source.taxes):
				target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
				if source.taxes[index].cost_center:
					target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)


		target.run_method("calculate_taxes_and_totals")
		target.debit_to = frappe.db.get_value("Company", target.company, "default_receivable_account")

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
				"serial_no": "serial_no_ref",
				"batch_no": "batch_ref",
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
				"batch_no"
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

def validate_no_of_boxes(self):
	for item in self.items:
		qty_per_box = frappe.db.get_value("Item",item.item_code,"qty_per_box")
		if qty_per_box:
			item.db_set("qty_per_box",flt(qty_per_box))
			item.db_set("no_of_boxes",flt(item.qty) / flt(qty_per_box))
			item.db_update()

def serial_no_validate(self):
	for item in self.items:
		if self.doctype == "Stock Entry":
			item_warehouse = item.s_warehouse
		else:
			item_warehouse = item.warehouse
			
		if item.serial_no:
			if item.serial_no.find(" ") != -1:
				item.serial_no = item.serial_no.replace(" ","")

		if item.serial_no and item_warehouse:
				
			serial_nos = get_serial_nos(item.serial_no) if item.serial_no else []
			item_det = get_item_details(item.item_code)



			if item_det.has_serial_no==0:
				if serial_nos:
					frappe.throw(_("Item {0} is not setup for Serial Nos. Column must be blank").format(item.item_code),
						SerialNoNotRequiredError)

			elif self._action == "submit":
				if serial_nos:
					if cint(item.qty) != flt(item.qty):
						frappe.throw(_("Serial No {0} quantity {1} cannot be a fraction").format(item.item_code, item.qty))

					if len(serial_nos) and len(serial_nos) != abs(cint(item.qty)):
						frappe.throw(_("{0} Serial Numbers required for Item {1}. You have provided {2}.").format(abs(item.qty), item.item_code, len(serial_nos)),
							SerialNoQtyError)

					if len(serial_nos) != len(set(serial_nos)):
						frappe.throw(_("Duplicate Serial No entered for Item {0}").format(item.item_code), SerialNoDuplicateError)

					
					for serial_no in serial_nos:
					
						if frappe.db.exists("Serial No", serial_no):
							sr = frappe.db.get_value("Serial No", serial_no, ["name", "item_code", "batch_no", "sales_order",
								"delivery_document_no", "delivery_document_type", "warehouse",
								"purchase_document_no", "company"], as_dict=1)
							#finbyz changes Start
							if sr.item_code:
								#finbyz Changes End
								if sr.item_code!=item.item_code:
									frappe.throw(_("Serial No {0} does not belong to Item {1}").format(serial_no,
										item.item_code), SerialNoItemError)

							if has_duplicate_serial_no(self,sr, item):
								frappe.throw(_("Serial No {0} has already been received").format(serial_no),
									SerialNoDuplicateError)

							if (sr.delivery_document_no and self.doctype not in ['Stock Entry', 'Stock Reconciliation']
									and self.name == sr.delivery_document_type):
										if self.return_against and self.return_against != sr.delivery_document_no:
											frappe.throw(_("Serial no {0} has been already returned").format(sr.name)) 

							if sr.warehouse!=item_warehouse:
								frappe.throw(_("Serial No {0} does not belong to Warehouse {1}").format(serial_no,
									item_warehouse), SerialNoWarehouseError)

							if self.doctype in ["Delivery Note"]:
								if sr.batch_no and sr.batch_no != item.batch_no:
									frappe.throw(_("Serial No {0} does not belong to Batch {1}").format(serial_no,
										item.batch_no), SerialNoBatchError)
								if not sr.warehouse:
									frappe.throw(_("Serial No {0} does not belong to any Warehouse")
										.format(serial_no), SerialNoWarehouseError)

							# if Sales Order reference in Serial No validate the Delivery Note or Invoice is against the same
							if sr.sales_order:
								if self.doctype == "Delivery Note":
									if item.against_sales_order != sr.sales_order:
										if not item.against_sales_invoice or frappe.db.exists("Sales Invoice Item",
											{"parent": item.against_sales_invoice, "item_code": item.item_code,
											"sales_order": sr.sales_order}):
											frappe.throw(_("Cannot deliver Serial No {0} of item {1} as it is reserved to \
												fullfill Sales Order {2}").format(sr.name, item.item_code, sr.sales_order))

							# if Sales Order reference in Delivery Note or Invoice validate SO reservations for item
							if self.doctype == "Delivery Note":
								if item.against_sales_order and get_reserved_qty_for_so(item.against_sales_order, item.item_code):
									validate_so_serial_no(sr, item.against_sales_order)
								else:
									if item.against_sales_invoice:
										sales_order = frappe.db.get_value("Sales Invoice Item", {
											"parent": item.against_sales_invoice, "item_code": item.item_code}, "sales_order")
										if sales_order and get_reserved_qty_for_so(sales_order, item.item_code):
											validate_so_serial_no(sr, sales_order)
						elif hasattr(self,'is_return'):
							if not self.is_return:
								# transfer out
								frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)
						else:
							frappe.throw(_("Serial No {0} not in stock").format(serial_no), SerialNoNotExistsError)

				else:
					frappe.throw(_("Serial Nos Required for Serialized Item {0}").format(item.item_code),
						SerialNoRequiredError)

			elif serial_nos and self._action == "cancel":
				for serial_no in serial_nos:
					sr = frappe.db.get_value("Serial No", serial_no, ["name", "warehouse"], as_dict=1)

					if sr and sr.warehouse != item_warehouse:
						frappe.throw(_("Cannot cancel {0} {1} because Serial No {2} does not belong to the warehouse {3}")
							.format(self.doctype, self.name, serial_no, item_warehouse))


def has_duplicate_serial_no(self,sr, item):
	# if sr.warehouse:
	# 	return True

	if sr.company != self.company:
		return False

	status = False
	if sr.purchase_document_no:
		if self.doctype in ['Purchase Receipt', 'Stock Entry', "Purchase Invoice"] and sr.delivery_document_type not in ['Purchase Receipt', 'Stock Entry', 'Purchase Invoice']:
			status = True

		if status and self.doctype == 'Stock Entry' and self.purpose != 'Material Receipt':
				status = False

	return status