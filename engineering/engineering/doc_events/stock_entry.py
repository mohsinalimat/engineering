import frappe
from frappe import _
from frappe.utils import cstr, flt
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost
from erpnext.stock.doctype.item.item import get_item_defaults
from six import itervalues

def on_cancel(self, method):
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()

def on_submit(self, method):
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()
	create_stock_entry(self)

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]

def before_validate(self,method):
	pass
	#calculate_rate_for_finish_item(self)

def calculate_rate_for_finish_item(self):
	if self.purpose in ["Manufacture", "Repack"]:
		raw_material_cost = 0
		for d in self.get("items"):
			if not d.t_warehouse and self.work_order \
				and frappe.db.get_single_value("Manufacturing Settings", "material_consumption"):
				raw_material_cost += (flt(d.qty)*flt(d.basic_rate))

		if raw_material_cost:
			d.basic_rate = flt((raw_material_cost) / flt(d.qty), d.precision("basic_rate"))
			d.basic_amount = flt((raw_material_cost), d.precision("basic_amount"))
	
def get_items(self):
	self.set('items', [])
	self.validate_work_order()
	if not self.posting_date or not self.posting_time:
		frappe.throw(_("Posting date and posting time is mandatory"))

	self.set_work_order_details()

	if self.bom_no:

		if self.purpose in ["Material Issue", "Material Transfer", "Manufacture", "Repack",
				"Send to Subcontractor", "Material Transfer for Manufacture", "Material Consumption for Manufacture"]:

			if self.work_order and self.purpose == "Material Transfer for Manufacture":
				item_dict = self.get_pending_raw_materials()
				if self.to_warehouse and self.pro_doc:
					for item in itervalues(item_dict):
						item["to_warehouse"] = self.pro_doc.wip_warehouse
				self.add_to_stock_entry_detail(item_dict)

			elif (self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture")
				and not self.pro_doc.skip_transfer and frappe.db.get_single_value("Manufacturing Settings",
				"backflush_raw_materials_based_on")== "Material Transferred for Manufacture"):
				self.get_transfered_raw_materials()

			elif self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture") and \
				frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "BOM": #finbyz changes (remove condition)
				get_unconsumed_raw_materials(self)
			else:
				if not self.fg_completed_qty:
					frappe.throw(_("Manufacturing Quantity is mandatory"))

				item_dict = self.get_bom_raw_materials(self.fg_completed_qty)

				#Get PO Supplied Items Details
				if self.purchase_order and self.purpose == "Send to Subcontractor":
					#Get PO Supplied Items Details
					item_wh = frappe._dict(frappe.db.sql("""
						select rm_item_code, reserve_warehouse
						from `tabPurchase Order` po, `tabPurchase Order Item Supplied` poitemsup
						where po.name = poitemsup.parent
							and po.name = %s""",self.purchase_order))

				for item in itervalues(item_dict):
					if self.pro_doc and (cint(self.pro_doc.from_wip_warehouse) or not self.pro_doc.skip_transfer):
						item["from_warehouse"] = self.pro_doc.wip_warehouse
					#Get Reserve Warehouse from PO
					if self.purchase_order and self.purpose=="Send to Subcontractor":
						item["from_warehouse"] = item_wh.get(item.item_code)
					item["to_warehouse"] = self.to_warehouse if self.purpose=="Send to Subcontractor" else ""

				self.add_to_stock_entry_detail(item_dict)

			if self.purpose != "Send to Subcontractor" and self.purpose in ["Manufacture", "Repack"]:
				scrap_item_dict = self.get_bom_scrap_material(self.fg_completed_qty)
				for item in itervalues(scrap_item_dict):
					if self.pro_doc and self.pro_doc.scrap_warehouse:
						item["to_warehouse"] = self.pro_doc.scrap_warehouse

				self.add_to_stock_entry_detail(scrap_item_dict, bom_no=self.bom_no)

		# fetch the serial_no of the first stock entry for the second stock entry
		if self.work_order and self.purpose == "Manufacture":
			self.set_serial_nos(self.work_order)
			work_order = frappe.get_doc('Work Order', self.work_order)
			add_additional_cost(self, work_order)

		# add finished goods item
		if self.purpose in ("Manufacture", "Repack"):
			self.load_items_from_bom()

	self.set_actual_qty()
	self.calculate_rate_and_amount(update_finished_item_rate=True) # finbyz changes in args

def get_unconsumed_raw_materials(self):
	wo = frappe.get_doc("Work Order", self.work_order)
	wo_items = frappe.get_all('Work Order Item',
		filters={'parent': self.work_order},
		fields=["item_code", "required_qty", "consumed_qty","allow_alternative_item"]
		)

	for item in wo_items:
		qty = item.required_qty

		item_account_details = get_item_defaults(item.item_code, self.company)
		# Take into account consumption if there are any.
		if self.purpose == 'Manufacture':
			req_qty_each = flt(item.required_qty / wo.qty)
			if (flt(item.consumed_qty) != 0):
				remaining_qty = flt(item.consumed_qty) - (flt(wo.produced_qty) * req_qty_each)
				exhaust_qty = req_qty_each * wo.produced_qty
				if remaining_qty > exhaust_qty :
					if (remaining_qty/(req_qty_each * flt(self.fg_completed_qty))) >= 1:
						qty =0
					else:
						qty = (req_qty_each * flt(self.fg_completed_qty)) - remaining_qty
			else:
				qty = req_qty_each * flt(self.fg_completed_qty)

		if qty > 0:
			self.add_to_stock_entry_detail({
				item.item_code: {
					"from_warehouse": wo.wip_warehouse,
					"to_warehouse": "",
					"qty": qty,
					"item_name": item.item_name,
					"description": item.description,
					"stock_uom": item_account_details.stock_uom,
					"expense_account": item_account_details.get("expense_account"),
					"cost_center": item_account_details.get("buying_cost_center"),
					"allow_alternative_item": item.allow_alternative_item, #finbyz
				}
			})

def create_stock_entry(self):
	def get_stock_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = frappe.db.get_value("Company", source.company, "alternate_company")

			target_run("set_missing_value")
		
		def update_details(source_doc, target_doc, source_parent):
			source_company = source_parent.company
			target_company = frappe.db.get_value("Company", source_company, "alternate_company")

			source_abbr = frappe.db.get_value("Company", source_company,'abbr')
			target_abbr = frappe.db.get_value("Company", target_company,'abbr')

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_abbr, target_abbr)

			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_abbr, target_abbr)

		fields = {
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {

				},
				"field_no_map": [
					"from_warehouse",
					"scan_barcode",
					"reference_doctype",
					"reference_docname",
					"company_series",
					"authority",
					"remark",
					"is_opening"
				]
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detain",
				"field_map": {
					"item_series": "item_code"
				},
				"field_no_map": [
					"item_series",
					"expense_account",
					"cost_center",
					"s_warehouse",
					"t_warehouse",
					"barcode",
					"batch_no",
					"serial_no",
				],
				"postprocess": update_details
			}
		}
	
		doclist = get_mapped_doc(
			"Sales Invoice",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doclist
	authority = authority = frappe.db.get_value("Company", self.company, "authority")
	if authority == "Authorized":
		se = get_stock_entry(self.name)

		se.naming_series = "A" + self.naming_series

		se.save(ignore_permissions = True)
		se.submit()