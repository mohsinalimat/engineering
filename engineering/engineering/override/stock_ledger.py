import frappe
from frappe import _, ValidationError
from frappe.utils import cint, flt, formatdate, format_time
from erpnext.stock.stock_ledger import (set_as_cancel,validate_cancellation,
		get_args_for_future_sle,get_previous_sle,validate_serial_no)
from erpnext.stock.utils import get_incoming_outgoing_rate_for_cancel
from six import iteritems

class NegativeStockError(ValidationError): pass

_exceptions = frappe.local('stockledger_exceptions')

# update_entries_after class method override
def raise_exceptions(self):
	msg_list = []
	for warehouse, exceptions in iteritems(self.exceptions):
		deficiency = min(e["diff"] for e in exceptions)

		if ((exceptions[0]["voucher_type"], exceptions[0]["voucher_no"]) in
			frappe.local.flags.currently_saving):

			msg = _("{0} units of {1} needed in {2} to complete this transaction.").format(
				abs(deficiency), frappe.get_desk_link('Item', exceptions[0]["item_code"]),
				frappe.get_desk_link('Warehouse', warehouse))
		else:
			msg = _("{0} units of {1} needed in {2} on {3} {4} for {5} to complete this transaction.").format(
				abs(deficiency), frappe.get_desk_link('Item', exceptions[0]["item_code"]),
				frappe.get_desk_link('Warehouse', warehouse),
				exceptions[0]["posting_date"], exceptions[0]["posting_time"],
				frappe.get_desk_link(exceptions[0]["voucher_type"], exceptions[0]["voucher_no"]))

		if msg:
			# FinByz Changes Start
			allow_negative_stock = frappe.db.get_value("Company", self.company, "allow_negative_stock")
			if not allow_negative_stock:
		   		msg_list.append(msg)
			# Finbyz Changes End
	
	if msg_list:
		message = "\n\n".join(msg_list)
		if self.verbose:
			frappe.throw(message, NegativeStockError, title='Insufficient Stock')
		else:
			raise NegativeStockError(message)

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


def make_sl_entries(sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
	from erpnext.controllers.stock_controller import future_sle_exists
	if sl_entries:
		from erpnext.stock.utils import update_bin

		cancel = sl_entries[0].get("is_cancelled")
		if cancel:
			validate_cancellation(sl_entries)
			set_as_cancel(sl_entries[0].get('voucher_type'), sl_entries[0].get('voucher_no'))

		args = get_args_for_future_sle(sl_entries[0])
		future_sle_exists(args, sl_entries)

		for sle in sl_entries:

			# Finbyz Changes Start
			# if sle.serial_no:
			# 	validate_serial_no(sle)
			# Finbyz Changes End

			if cancel:
				sle['actual_qty'] = -flt(sle.get('actual_qty'))

				if sle['actual_qty'] < 0 and not sle.get('outgoing_rate'):
					sle['outgoing_rate'] = get_incoming_outgoing_rate_for_cancel(sle.item_code,
						sle.voucher_type, sle.voucher_no, sle.voucher_detail_no)
					sle['incoming_rate'] = 0.0

				if sle['actual_qty'] > 0 and not sle.get('incoming_rate'):
					sle['incoming_rate'] = get_incoming_outgoing_rate_for_cancel(sle.item_code,
						sle.voucher_type, sle.voucher_no, sle.voucher_detail_no)
					sle['outgoing_rate'] = 0.0

			if sle.get("actual_qty") or sle.get("voucher_type")=="Stock Reconciliation":
				# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
				sle_doc = make_entry(sle, allow_negative_stock, via_landed_cost_voucher,sle.get('change_rate'))
				# Finbyz Changes End

			args = sle_doc.as_dict()

			# Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
			args.update({
				"change_rate":sle.get('change_rate') or False
			})
			# Finbyz Changes End

			if sle.get("voucher_type") == "Stock Reconciliation":
				# preserve previous_qty_after_transaction for qty reposting
				args.previous_qty_after_transaction = sle.get("previous_qty_after_transaction")

			update_bin(args, allow_negative_stock, via_landed_cost_voucher)

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
	return sle