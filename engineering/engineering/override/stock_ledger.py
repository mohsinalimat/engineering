import frappe
from frappe import _, ValidationError
from frappe.utils import cint, flt, formatdate, format_time
from erpnext.stock.stock_ledger import get_previous_sle
from erpnext.stock.stock_ledger import set_as_cancel,delete_cancelled_entry

class NegativeStockError(ValidationError): pass

# update_entries_after class method override
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

	# FinByz Changes Start
	allow_negative_stock = frappe.db.get_value("Company", self.company, "allow_negative_stock")
	
	if not allow_negative_stock:
		if self.verbose:
			frappe.throw(msg, NegativeStockError, title='Insufficent Stock')
		else:
			raise NegativeStockError(msg)
	# Finbyz Changes End

def set_actual_qty(self):
	# FinByz Changes Start
	allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock")) or cint(frappe.db.get_value("Company", self.company, "allow_negative_stock"))
	# FinByz Changes End

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


def make_sl_entries(sl_entries, is_amended=None, allow_negative_stock=False, via_landed_cost_voucher=False,change_rate=False):
	frappe.msgprint("called from stock_ledger override")
	if sl_entries:
		from erpnext.stock.utils import update_bin

		cancel = True if sl_entries[0].get("is_cancelled") == "Yes" else False
		if cancel:
			set_as_cancel(sl_entries[0].get('voucher_no'), sl_entries[0].get('voucher_type'))

		for sle in sl_entries:
			sle_id = None
			if sle.get('is_cancelled') == 'Yes':
				sle['actual_qty'] = -flt(sle['actual_qty'])
			if sle.get("actual_qty") or sle.get("voucher_type")=="Stock Reconciliation":
				# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
				sle_id = make_entry(sle, allow_negative_stock, via_landed_cost_voucher,sle.get('change_rate'))
				# Finbyz Changes End
			args = sle.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended,
				# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
				"change_rate":sle.get('change_rate') or False
				# Finbyz Changes End
			})
			update_bin(args, allow_negative_stock, via_landed_cost_voucher)

		if cancel:
			delete_cancelled_entry(sl_entries[0].get('voucher_type'), sl_entries[0].get('voucher_no'))

def make_entry(args, allow_negative_stock=False, via_landed_cost_voucher=False,change_rate=False):
	args.update({"doctype": "Stock Ledger Entry"})
	sle = frappe.get_doc(args)
	sle.flags.ignore_permissions = 1
	sle.allow_negative_stock=allow_negative_stock
	sle.via_landed_cost_voucher = via_landed_cost_voucher

	# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
	sle.change_rate = change_rate
	# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice

	sle.insert()
	sle.submit()
	return sle.name