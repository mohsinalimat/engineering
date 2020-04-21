import frappe
from frappe import _
from frappe.utils import cstr, flt
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost
from erpnext.stock.doctype.item.item import get_item_defaults
from six import itervalues
from frappe.model.mapper import get_mapped_doc


def on_trash(self, method):
	se_list = []
	if self.se_ref:
		se_list.append(self.se_ref)
		if frappe.db.exists("Stock Entry", self.se_ref):
			se_doc = frappe.get_doc("Stock Entry", self.se_ref)
			
			if se_doc.jw_ref:
				se_list.append(se_doc.jw_ref)

			if se_doc.se_ref:
				se_list.append(se_doc.se_ref)
	
	if self.jw_ref:
		se_list.append(self.jw_ref)
		if frappe.db.exists("Stock Entry", self.jw_ref):
			jw_doc = frappe.get_doc("Stock Entry", self.jw_ref)

			if jw_doc.jw_ref:
				se_list.append(jw_doc.jw_ref)

			if jw_doc.se_ref:
				se_list.append(jw_doc.se_ref)

	se_list = list(set(se_list))

	for item in se_list:
		frappe.db.set_value("Stock Entry", item, 'se_ref', None)
		frappe.db.set_value("Stock Entry", item, 'jw_ref', None)
	
	for item in se_list:
		if self.name != item:
			frappe.delete_doc("Stock Entry", item)

def on_cancel(self, method):
	# self.flags.ignore_links = True
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()
	cancel_job_work(self)

def cancel_job_work(self):
	if self.jw_ref:
		jw_doc = frappe.get_doc("Stock Entry", self.jw_ref)
		jw_doc.flags.ignore_links = True

		if jw_doc.docstatus == 1:
			jw_doc.cancel()
	
	if self.se_ref:
		se_doc = frappe.get_doc("Stock Entry", self.se_ref)
		se_doc.flags.ignore_links = True

		if se_doc.docstatus == 1:
			se_doc.cancel()

def on_submit(self, method):
	create_stock_entry(self)
	create_job_work_receipt_entry(self)
	save_serial_no(self)
	setting_references(self)

def setting_references(self):
	if not self.se_ref and self.jw_ref:
		ref = frappe.db.get_value("Stock Entry", {"se_ref": self.jw_ref}, 'jw_ref')
		self.db_set("se_ref", ref)
		frappe.db.set_value("Stock Entry", ref, 'se_ref', self.name)

def save_serial_no(self):
	for item in self.items:
		if item.serial_no:
			for serial_no in get_serial_nos(item.serial_no):
				doc = frappe.get_doc("Serial No", serial_no)
				doc.save()

def get_serial_nos(serial_no):
	return [s.strip() for s in cstr(serial_no).strip().upper().replace(',', '\n').split('\n')
		if s.strip()]

def before_validate(self,method):
	pass
	
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
	company = self.company
	def get_stock_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_value(source, target):
			target.company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.from_job_work = 1
			if source.send_to_company:
				target.job_work_company = frappe.db.get_value("Company", source.job_work_company, 'alternate_company')

			if source.stock_entry_type == "Manufacture":
				target.stock_entry_type = "Manufacturing"
			
			if source.stock_entry_type == "Material Transfer for Manufacture":
				target.stock_entry_type = "Material Transfer"
			
			source_abbr = frappe.db.get_value("Company", source.company,'abbr')
			target_abbr = frappe.db.get_value("Company", target.company,'abbr')
			
			if source.from_warehouse:
				target.from_warehouse = source.from_warehouse.replace(source_abbr, target_abbr)

			if source.to_warehouse:
				target.to_warehouse = source.to_warehouse.replace(source_abbr, target_abbr)

			if self.amended_from:
				target.amended_from = frappe.db.get_value("Stock Entry", {'se_ref': self.amended_from}, "name")

			target.run_method("set_missing_value")
		
		def update_details(source_doc, target_doc, source_parent):
			source_company = source_parent.company
			target_company = frappe.db.get_value("Company", source_company, "alternate_company")

			source_abbr = frappe.db.get_value("Company", source_company,'abbr')
			target_abbr = frappe.db.get_value("Company", target_company,'abbr')

			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_abbr, target_abbr)

			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_abbr, target_abbr)
			
			if source_doc.s_warehouse:
				target_doc.s_warehouse = source_doc.s_warehouse.replace(source_abbr, target_abbr)
			
			if source_doc.t_warehouse:
				target_doc.t_warehouse = source_doc.t_warehouse.replace(source_abbr, target_abbr)
			
			if source_parent.stock_entry_type == "Material Receipt":
				target_doc.basic_rate = source_doc.basic_rate

		def update_account(source_doc, target_doc, source_parent):
			source_company = source_parent.company
			target_company = frappe.db.get_value("Company", source_company, "alternate_company")

			source_abbr = frappe.db.get_value("Company", source_company,'abbr')
			target_abbr = frappe.db.get_value("Company", target_company,'abbr')

			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_abbr, target_abbr)

		fields = {
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {
					"name": "se_ref",
					"reference_doctype": "reference_doctype",
					"reference_docname": "reference_docname",
				},
				"field_no_map": [
					"from_warehouse",
					"to_warehouse"
					"scan_barcode",
					"company_series",
					"authority",
					"remark",
					"is_opening",
					"purpose",
					"jw_ref",
				]
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"item_series": "item_code",
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
					"basic_rate",
					"work_order",
					"bom_no",
					"fg_completed_qty",
					"use_multi_level_bom"
				],
				"postprocess": update_details
			},
			'Landed Cost Taxes and Charges':{
				"doctype": "Landed Cost Taxes and Charges",
				"postprocess": update_account
			}
		}
	
		doclist = get_mapped_doc(
			"Stock Entry",
			source_name,
			fields,
			target_doc,
			set_missing_value,
			ignore_permissions=ignore_permissions
		)

		return doclist
	authority = authority = frappe.db.get_value("Company", self.company, "authority")
	if authority == "Unauthorized" and self.replicate and not self.se_ref and not self.jw_ref:
		se = get_stock_entry(self.name)

		se.save(ignore_permissions = True)

		# self.company = se.company
		if se.stock_entry_type in ['Material Transfer', 'Material Issue', 'Repack', "Manufacturing","Jobwork Manufacturing"]:
			se.get_stock_and_rate()
		se.save(ignore_permissions = True)
		# frappe.flags.warehouse_account_map = None
		se.submit()
		# self.company = company
		self.db_set('se_ref', se.name)
		self.se_ref = se.name

@frappe.whitelist()
def submit_stock_entry(name):
	doc = frappe.get_doc("Stock Entry", name)
	frappe.msgprint(str(doc.name))
	if doc.docstatus == 0:
		doc.save(ignore_permissions = True)
		if doc.stock_entry_type in ['Jobwork Manufacturing', 'Send Jobwork Finish', 'Material Transfer', 'Material Issue', 'Repack', "Manufacturing"]:
			doc.get_stock_and_rate()
			doc.calculate_rate_and_amount()
		
		doc.flags.ignore_permissions = True
		doc.submit()

		return doc.jw_ref

@frappe.whitelist()
def submit_job_work_entry(name):
	doc = frappe.get_doc("Stock Entry", name)
	frappe.msgprint(str(doc.name))
	if doc.docstatus == 0:
		doc.save(ignore_permissions = True)
		if doc.stock_entry_type in ['Jobwork Manufacturing', 'Send Jobwork Finish', 'Material Transfer', 'Material Issue', 'Repack', "Manufacturing"]:
			doc.get_stock_and_rate()
			doc.calculate_rate_and_amount()
		
		doc.flags.ignore_permissions = True
		doc.submit()

		return doc.se_ref

@frappe.whitelist()
def create_job_work_receipt_entry(self):
	if self.stock_entry_type == "Send to Jobwork" and self.purpose == "Material Transfer" and self.send_to_company and not self.jw_ref:

		source_abbr = frappe.db.get_value("Company", self.company,'abbr')
		target_abbr = frappe.db.get_value("Company", self.job_work_company,'abbr')
		expense_account = frappe.db.get_value('Company',self.job_work_company,'job_work_difference_account')
		job_work_warehouse = frappe.db.get_value('Company',self.job_work_company,'job_work_warehouse')

		if not expense_account or not job_work_warehouse:
			frappe.throw(_("Please set Job work difference account and warehouse in company <b>{0}</b>").format(self.job_work_company))

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Receive Jobwork Raw Material"
		se.replicate = self.replicate
		se.purpose = "Material Receipt"
		se.set_posting_time = 1
		se.jw_ref = self.name
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.company = self.job_work_company
		se.to_warehouse = job_work_warehouse

		if self.amended_from:
			se.amended_from = frappe.db.get_value("Stock Entry", {'jw_ref': self.amended_from}, "name")
		for row in self.items:
			se.append("items",{
				'item_code': row.item_code,
				't_warehouse': job_work_warehouse,
				'qty': row.qty,
				'expense_account': expense_account,
				'cost_center': row.cost_center.replace(source_abbr, target_abbr)
			})
		
		if self.additional_costs:
			for row in self.additional_costs:
				se.append("additional_costs",{
					'description': row.description,
					'amount': row.amount
				})
		
		se.save(ignore_permissions=True)
		self.db_set('jw_ref', se.name)
		# frappe.flags.warehouse_account_map = None
		self.jw_ref = se.name
		se.submit()
