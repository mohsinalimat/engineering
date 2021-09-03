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

                if d.from_warehouse and ((not cint(self.is_return) and self.docstatus==1)
                    or (cint(self.is_return) and self.docstatus==2)):
                    from_warehouse_sle = self.get_sl_entries(d, {
                        "actual_qty": -1 * pr_qty,
                        "warehouse": d.from_warehouse,
                        "outgoing_rate": d.rate,
                        "recalculate_rate": 1,
                        "dependant_sle_voucher_detail_no": d.name
                    })

                    sl_entries.append(from_warehouse_sle)

                sle = self.get_sl_entries(d, {
                    "actual_qty": flt(pr_qty),
                    "serial_no": cstr(d.serial_no).strip()
                })
                if self.is_return:
                    outgoing_rate = get_rate_for_return(self.doctype, self.name, d.item_code, self.return_against, item_row=d)

                    sle.update({
                        "outgoing_rate": outgoing_rate,
                        "recalculate_rate": 1
                    })
                    if d.from_warehouse:
                        sle.dependant_sle_voucher_detail_no = d.name
                else:
                    val_rate_db_precision = 6 if cint(self.precision("valuation_rate", d)) <= 6 else 9
                    incoming_rate = flt(d.valuation_rate, val_rate_db_precision)
                    sle.update({
                        "incoming_rate": incoming_rate,
                        "recalculate_rate": 1 if (self.is_subcontracted and d.bom) or d.from_warehouse else 0
                    })
                # Finbyz Changes: change_rate of purchase_receipt from purchase_invoice
                sle.update({"change_rate":self.get('change_rate') or False
                })
                # Finbyz Changes End
                sl_entries.append(sle)

                if d.from_warehouse and ((not cint(self.is_return) and self.docstatus==2)
                    or (cint(self.is_return) and self.docstatus==1)):
                    from_warehouse_sle = self.get_sl_entries(d, {
                        "actual_qty": -1 * pr_qty,
                        "warehouse": d.from_warehouse,
                        "recalculate_rate": 1
                    })

                    sl_entries.append(from_warehouse_sle)

            if flt(d.rejected_qty) != 0:
                sl_entries.append(self.get_sl_entries(d, {
                    "warehouse": d.rejected_warehouse,
                    "actual_qty": flt(d.rejected_qty) * flt(d.conversion_factor),
                    "serial_no": cstr(d.rejected_serial_no).strip(),
                    "incoming_rate": 0.0
                }))

    self.make_sl_entries_for_supplier_warehouse(sl_entries)
    self.make_sl_entries(sl_entries, allow_negative_stock=allow_negative_stock,
        via_landed_cost_voucher=via_landed_cost_voucher)