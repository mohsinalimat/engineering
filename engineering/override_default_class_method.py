import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, format_time
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError


def raise_exceptions(self):
	deficiency = min(e["diff"] for e in self.exceptions)

	if ((self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]) in
		frappe.local.flags.currently_saving):

		msg = _("{0} units of {1} needed in {2} to complete this transaction.").format(
			abs(deficiency), frappe.get_desk_link('Item', self.item_code),
			frappe.get_desk_link('Warehouse', self.warehouse))
	else:
		msg = _("{0} units of {1} needed in {2} on {3} {4} for {5} to complete this transaction.").format(
			abs(deficiency), frappe.get_desk_link('Item', self.item_code),
			frappe.get_desk_link('Warehouse', self.warehouse),
			self.exceptions[0]["posting_date"], self.exceptions[0]["posting_time"],
			frappe.get_desk_link(self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]))

	allow_negative_stock = frappe.db.get_value("Company", self.company, "allow_negative_stock")
	
	if not allow_negative_stock:
		if self.verbose:
			frappe.throw(msg, NegativeStockError, title='Insufficent Stock')
		else:
			raise NegativeStockError(msg)

def set_actual_qty(self):
	allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock")) or cint(frappe.db.get_value("Company", self.company, "allow_negative_stock"))

	for d in self.get('items'):
		previous_sle = get_previous_sle({
			"item_code": d.item_code,
			"warehouse": d.s_warehouse or d.t_warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time
		})

		# get actual stock at source warehouse
		d.actual_qty = previous_sle.get("qty_after_transaction") or 0

		# validate qty during submit
		if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and flt(d.actual_qty, d.precision("actual_qty")) < flt(d.transfer_qty, d.precision("actual_qty")):
			frappe.throw(_("Row {0}: Quantity not available for {4} in warehouse {1} at posting time of the entry ({2} {3})").format(d.idx,
				frappe.bold(d.s_warehouse), formatdate(self.posting_date),
				format_time(self.posting_time), frappe.bold(d.item_code))
				+ '<br><br>' + _("Available quantity is {0}, you need {1}").format(frappe.bold(d.actual_qty),
					frappe.bold(d.transfer_qty)),
				NegativeStockError, title=_('Insufficient Stock'))

def validate_warehouse(self):
	if not self.get("__islocal"):
		item_code, warehouse = frappe.db.get_value("Serial No",
			self.name, ["item_code", "warehouse"])
		if item_code:	
			if not self.via_stock_ledger and item_code != self.item_code:
				frappe.throw(_("Item Code cannot be changed for Serial No."),
					SerialNoCannotCannotChangeError)
		if warehouse:
			if not self.via_stock_ledger and warehouse != self.warehouse:
				frappe.throw(_("Warehouse cannot be changed for Serial No."),
					SerialNoCannotCannotChangeError)

def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.tax_amount, tax.precision("tax_amount"))
			current_tax_amount = item.net_amount*actual / self.doc.net_total if self.doc.net_total else 0.0

		elif tax.charge_type == "On Net Total":
			if self.doc.authority == "Unauthorized":
				current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount
			else:
				current_tax_amount = (tax_rate / 100.0) * item.net_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item
		elif tax.charge_type == "On Item Quantity":
			current_tax_amount = tax_rate * item.stock_qty

		self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

		return current_tax_amount

def determine_exclusive_rate(self):
	if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
		return

	for item in self.doc.get("items"):
		item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
		cumulated_tax_fraction = 0
		for i, tax in enumerate(self.doc.get("taxes")):
			tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)

			if i==0:
				tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
			else:
				tax.grand_total_fraction_for_current_item = \
					self.doc.get("taxes")[i-1].grand_total_fraction_for_current_item \
					+ tax.tax_fraction_for_current_item

			cumulated_tax_fraction += tax.tax_fraction_for_current_item
		if cumulated_tax_fraction and not self.discount_amount_applied and item.qty:
			# Finbyz Changes for Tax Calculation on Real Rate
			if self.doc.authority == "Unauthorized":
				amount_diff = item.amount - item.discounted_amount
				item.discounted_net_amount = flt((item.amount - amount_diff) / (1 + cumulated_tax_fraction))
				
				try:
					item.discounted_net_rate = flt(item.discounted_net_amount / item.real_qty)
				except:
					item.discounted_net_rate = 0
								
				item.net_amount = item.amount - (item.discounted_amount - item.discounted_net_amount)
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			# Finbyz Changes end here.
			else:
				item.net_amount = flt(item.amount / (1 + cumulated_tax_fraction))
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			item.discount_percentage = flt(item.discount_percentage,
				item.precision("discount_percentage"))

			self._set_in_company_currency(item, ["net_rate", "net_amount"])