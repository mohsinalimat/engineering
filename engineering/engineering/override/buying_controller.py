from __future__ import unicode_literals
import frappe
from frappe.utils import flt,cint, cstr, getdate
from frappe import _, msgprint

def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
    self.update_ordered_and_reserved_qty()

    sl_entries = []
    stock_items = self.get_stock_items()

    for d in self.get('items'):
        if d.item_code in stock_items and d.warehouse:
            pr_qty = flt(d.qty) * flt(d.conversion_factor)

            if pr_qty:
                sle = self.get_sl_entries(d, {
                    "actual_qty": flt(pr_qty),
                    "serial_no": cstr(d.serial_no).strip()
                })
                if self.is_return:
                    filters = {
                        "voucher_type": self.doctype,
                        "voucher_no": self.return_against,
                        "item_code": d.item_code
                    }

                    if (self.doctype == "Purchase Invoice" and self.update_stock
                        and d.get("purchase_invoice_item")):
                        filters["voucher_detail_no"] = d.purchase_invoice_item
                    elif self.doctype == "Purchase Receipt" and d.get("purchase_receipt_item"):
                        filters["voucher_detail_no"] = d.purchase_receipt_item

                    original_incoming_rate = frappe.db.get_value("Stock Ledger Entry", filters, "incoming_rate")

                    sle.update({
                        "outgoing_rate": original_incoming_rate
                    })
                else:
                    val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
                    incoming_rate = flt(d.valuation_rate, val_rate_db_precision)
                    sle.update({
                        "incoming_rate": incoming_rate
                    })
                # Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
                sle.update({"change_rate":self.get('change_rate') or False
                })
                # Finbyz Changes End
                sl_entries.append(sle)

            if flt(d.rejected_qty) != 0:
                sl_entries.append(self.get_sl_entries(d, {
                    "warehouse": d.rejected_warehouse,
                    "actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
                    "serial_no": cstr(d.rejected_serial_no).strip(),
                    "incoming_rate": 0.0,
                }))
    self.make_sl_entries_for_supplier_warehouse(sl_entries)
    self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock,
        via_landed_cost_voucher=via_landed_cost_voucher)
