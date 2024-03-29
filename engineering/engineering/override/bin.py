from __future__ import unicode_literals
import frappe
from frappe.utils import flt, nowdate
import frappe.defaults

def update_stock(self, args, allow_negative_stock=False, via_landed_cost_voucher=False):
    '''Called from erpnext.stock.utils.update_bin'''
    self.update_qty(args)

    if args.get("actual_qty") or args.get("voucher_type") == "Stock Reconciliation":
        from erpnext.stock.stock_ledger import update_entries_after, update_qty_in_future_sle

        if not args.get("posting_date"):
            args["posting_date"] = nowdate()

        if args.get("is_cancelled") and via_landed_cost_voucher:
            return

        # Reposts only current voucher SL Entries
        # Updates valuation rate, stock value, stock queue for current transaction
        update_entries_after({
            "item_code": self.item_code,
            "warehouse": self.warehouse,
            "posting_date": args.get("posting_date"),
            "posting_time": args.get("posting_time"),
            "voucher_type": args.get("voucher_type"),
            "voucher_no": args.get("voucher_no"),
            "sle_id": args.name,
            "creation": args.creation,
            # Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
            "change_rate":args.get('change_rate') or False
            # Finbyz Changes End
        }, allow_negative_stock=allow_negative_stock, via_landed_cost_voucher=via_landed_cost_voucher)

        # update qty in future ale and Validate negative qty
        update_qty_in_future_sle(args, allow_negative_stock)
