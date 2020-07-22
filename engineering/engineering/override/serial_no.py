import frappe
from frappe import _, ValidationError
from erpnext.stock.doctype.serial_no.serial_no import SerialNoCannotCannotChangeError


# SerialNo class method override
def validate_warehouse(self):
	if not self.get("__islocal"):
		item_code, warehouse = frappe.db.get_value("Serial No",
			self.name, ["item_code", "warehouse"])

		# FinByz Changes Start
		# if item_code:	
		# 	if not self.via_stock_ledger and item_code != self.item_code:
		# 		frappe.throw(_("Item Code cannot be changed for Serial No."),
		# 			SerialNoCannotCannotChangeError)
		# if warehouse:
		# 	if not self.via_stock_ledger and warehouse != self.warehouse:
		# 		frappe.throw(_("Warehouse cannot be changed for Serial No."),
		# 			SerialNoCannotCannotChangeError)
		pass
		# FinByz Changes End