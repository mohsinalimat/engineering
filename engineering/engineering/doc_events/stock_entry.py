import frappe
from frappe import _
from frappe.utils import cstr, flt, cint
from erpnext.manufacturing.doctype.bom.bom import add_additional_cost
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.stock.doctype.stock_entry.stock_entry import get_used_alternative_items
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from engineering.engineering.doc_events.delivery_note import serial_no_validate

from six import itervalues
from frappe.model.mapper import get_mapped_doc

def validate(self, method):
	if self.stock_entry_type == "Material Receipt":
		if not "Local Admin" in frappe.get_roles(frappe.session.user):
			frappe.throw("You are Not Allowed to Create Material Receipt Entry.")
	if self._action in ['submit','cancel']:
		serial_no_validate(self)
	if self.purpose in ['Repack','Manufacture','Material Issue']:
		self.get_stock_and_rate()
	#validate_additional_cost(self)
	validate_transfer_item(self)
	validate_item_packing(self)

	if self.purpose in ['Repack','Manufacture']:
		self.calculate_rate_and_amount(force=True)

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

def before_cancel(self, method):
	cancel_job_work(self)

def on_cancel(self, method):
	remove_ref_from_item_packing(self)

def cancel_job_work(self):
	if self.jw_ref:
		jw_doc = frappe.get_doc("Stock Entry", self.jw_ref)
		self.db_set('jw_ref',None)
		self.db_update()
		if jw_doc.docstatus == 1:
			jw_doc.flags.ignore_links = True
			jw_doc.db_set('jw_ref',None)
			jw_doc.cancel()
	if self.se_ref:
		se_doc = frappe.get_doc("Stock Entry", self.se_ref)
		self.db_set('se_ref',None)
		self.db_update()
		if se_doc.docstatus == 1:
			se_doc.flags.ignore_links = True
			se_doc.db_set('se_ref',None)
			se_doc.cancel()

def on_submit(self, method):
	create_stock_entry(self)
	create_job_work_receipt_entry(self)
	create_job_work_receipt_entry_serialized_item(self)
	# save_serial_no(self)
	setting_references(self)

def setting_references(self):
	if not self.se_ref and self.jw_ref:
		ref = frappe.db.get_value("Stock Entry", {"se_ref": self.jw_ref}, 'jw_ref')
		self.db_set("se_ref", ref)
		frappe.db.set_value("Stock Entry", ref, 'se_ref', self.name)

def save_serial_no(self):
	# for item in self.items:
	# 	if item.serial_no:
	# 		for serial_no in get_serial_nos(item.serial_no):
	# 			doc = frappe.get_doc("Serial No", serial_no)
	# 			doc.save()
	pass

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
				frappe.db.get_single_value("Manufacturing Settings", "backflush_raw_materials_based_on")== "BOM" and \
				frappe.db.get_single_value("Manufacturing Settings", "material_consumption")== 1:
				self.get_unconsumed_raw_materials()
			
			elif self.work_order and (self.purpose == "Manufacture" or self.purpose == "Material Consumption for Manufacture"):
				if not self.fg_completed_qty:
					frappe.throw(_("Manufacturing Quantity is mandatory"))
				
				item_dict = get_work_order_raw_materials(self,self.fg_completed_qty)

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

		# fetch the serial_no of the first stock entry for the second stock entry
		if self.work_order and self.purpose == "Manufacture":
			self.set_serial_nos(self.work_order)
			work_order = frappe.get_doc('Work Order', self.work_order)
			add_additional_cost(self, work_order)

		# add finished goods item
		if self.purpose in ("Manufacture", "Repack"):
			self.load_items_from_bom()

	self.set_scrap_items()
	self.set_actual_qty()
	self.calculate_rate_and_amount(raise_error_if_no_rate=False,update_finished_item_rate=True) # finbyz changes in args

def get_work_order_raw_materials(self, qty):
	# item dict = { item_code: {qty, description, stock_uom} }
	item_dict = get_work_order_items_as_dict(self.work_order, self.company, qty=qty, fetch_qty_in_stock_uom=False)
	used_alternative_items = get_used_alternative_items(work_order = self.work_order)
	for item in itervalues(item_dict):
		# if source warehouse presents in BOM set from_warehouse as bom source_warehouse
		if item["allow_alternative_item"]:
			item["allow_alternative_item"] = frappe.db.get_value('Work Order',
				self.work_order, "allow_alternative_item")

		item.from_warehouse = self.from_warehouse or item.source_warehouse or item.default_warehouse
		if item.item_code in used_alternative_items:
			alternative_item_data = used_alternative_items.get(item.item_code)
			item.item_code = alternative_item_data.item_code
			item.item_name = alternative_item_data.item_name
			item.stock_uom = alternative_item_data.stock_uom
			item.uom = alternative_item_data.uom
			item.conversion_factor = alternative_item_data.conversion_factor
			item.description = alternative_item_data.description

	return item_dict

def get_work_order_items_as_dict(wo, company, qty=1, include_non_stock_items=False, fetch_qty_in_stock_uom=True):
	item_dict = {}

	# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
	query = """select
				wo_item.item_code,
				wo_item.idx,
				item.item_name,
				sum(wo_item.required_qty/ifnull(wo.qty, 1)) * %(qty)s as qty,
				item.allow_alternative_item,
				item_default.default_warehouse,
				item_default.expense_account as expense_account,
				item_default.buying_cost_center as cost_center
				{select_columns}
			from
				`tab{table}` wo_item
				JOIN `tabWork Order` wo ON wo_item.parent = wo.name
				JOIN `tabItem` item ON item.name = wo_item.item_code
				LEFT JOIN `tabItem Default` item_default
					ON item_default.parent = item.name and item_default.company = %(company)s
			where
				wo_item.docstatus < 2
				and wo.name = %(wo)s
				and item.is_stock_item in (1, {is_stock_item})
				{where_conditions}
				group by item_code, stock_uom
				order by idx"""

	is_stock_item = 0 if include_non_stock_items else 1
	conversion_factor = 1
	query = query.format(table="Work Order Item", where_conditions="", is_stock_item=is_stock_item,
		select_columns = """, item.stock_uom, wo_item.source_warehouse,
			wo_item.idx, wo_item.include_item_in_manufacturing,
			wo_item.description""")
	items = frappe.db.sql(query, {"qty": qty, "wo": wo, "company": company }, as_dict=True)
	for item in items:
		if item.item_code in item_dict:
			item_dict[item.item_code]["qty"] += flt(item.qty)
		else:
			item_dict[item.item_code] = item	
	return item_dict

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
			target.set_posting_time = 1
			if source.send_to_company:
				target.job_work_company = frappe.db.get_value("Company", source.job_work_company, 'alternate_company')

			if source.stock_entry_type == "Manufacture":
				target.stock_entry_type = "Manufacturing"
				target.work_order = source.work_order
			
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
					"posting_date": "posting_date",
					"poting_time": "posting_time",
					"work_order":"work_order",
				},
				"field_no_map": [
					"from_warehouse",
					"to_warehouse",
					"to_company_receive_warehouse",
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

		if se.stock_entry_type in ['Material Transfer', 'Material Issue', 'Repack', "Manufacturing","Jobwork Manufacturing","Manufacture"]:
			se.get_stock_and_rate()
		se.save(ignore_permissions = True)
		se.submit()
		self.db_set('se_ref', se.name)
		self.se_ref = se.name

@frappe.whitelist()
def submit_stock_entry(name):
	doc = frappe.get_doc("Stock Entry", name)
	#frappe.msgprint(str(doc.name))
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
	#frappe.msgprint(str(doc.name))
	if doc.docstatus == 0:
		doc.save(ignore_permissions = True)
		if doc.stock_entry_type in ['Jobwork Manufacturing', 'Send Jobwork Finish', 'Material Transfer', 'Material Issue', 'Repack', "Manufacturing"]:
			doc.get_stock_and_rate()
			doc.calculate_rate_and_amount()
		
		doc.flags.ignore_permissions = True
		doc.submit()

		return doc.se_ref

@frappe.whitelist()
def create_job_work_receipt_entry_serialized_item(self):
	if self.stock_entry_type == "Send Serialized Item" and self.purpose == "Material Issue" and self.send_to_company and not self.jw_ref:

		source_abbr = frappe.db.get_value("Company", self.company,'abbr')
		target_abbr = frappe.db.get_value("Company", self.job_work_company,'abbr')
		expense_account = frappe.db.get_value('Company',self.job_work_company,'job_work_difference_account')
		job_work_warehouse = frappe.db.get_value('Company',self.job_work_company,'job_work_warehouse')

		if not expense_account or not job_work_warehouse:
			frappe.throw(_("Please set Job work difference account and warehouse in company <b>{0}</b>").format(self.job_work_company))

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Receive Jobwork Serialized Item"
		se.replicate = self.replicate
		se.purpose = "Material Receipt"
		se.set_posting_time = 1
		se.jw_ref = self.name
		se.posting_date = self.posting_date
		se.posting_time = self.posting_time
		se.company = self.job_work_company
		se.to_warehouse = self.to_company_receive_warehouse or job_work_warehouse

		if self.amended_from:
			se.amended_from = frappe.db.get_value("Stock Entry", {'jw_ref': self.amended_from}, "name")
		for row in self.items:
			se.append("items",{
				'item_code': row.item_code,
				't_warehouse':  self.to_company_receive_warehouse or job_work_warehouse,
				'serial_no': row.serial_no,
				'basic_rate':row.basic_rate,
				'batch_no': row.batch_no,
				'qty': row.qty,
				'expense_account': expense_account,
				'cost_center': row.cost_center.replace(source_abbr, target_abbr)
			})
		
		if self.additional_costs:
			for row in self.additional_costs:
				se.append("additional_costs",{
					'expense_account': row.expense_account.replace(source_abbr, target_abbr),
					'description': row.description,
					'amount': row.amount
				})
		
		se.save(ignore_permissions=True)
		self.db_set('jw_ref', se.name)
		# frappe.flags.warehouse_account_map = None
		self.jw_ref = se.name
		se.submit()

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
		se.to_warehouse = self.to_company_receive_warehouse or job_work_warehouse

		if self.amended_from:
			se.amended_from = frappe.db.get_value("Stock Entry", {'jw_ref': self.amended_from}, "name")
		for row in self.items:
			se.append("items",{
				'item_code': row.item_code,
				't_warehouse':  self.to_company_receive_warehouse or job_work_warehouse,
				'serial_no': row.serial_no,
				'basic_rate':row.basic_rate,
				'batch_no': row.batch_no,
				'qty': row.qty,
				'expense_account': expense_account,
				'cost_center': row.cost_center.replace(source_abbr, target_abbr)
			})
		
		if self.additional_costs:
			for row in self.additional_costs:
				se.append("additional_costs",{
					'expense_account': row.expense_account.replace(source_abbr, target_abbr),
					'description': row.description,
					'amount': row.amount
				})
		
		se.save(ignore_permissions=True)
		self.db_set('jw_ref', se.name)
		# frappe.flags.warehouse_account_map = None
		self.jw_ref = se.name
		se.submit()


def validate_transfer_item(self):
	if self.purpose == "Material Transfer for Manufacture" and self.work_order:
		wo_item = [x.item_code for x in frappe.get_list("Work Order Item",{'parent':self.work_order},'item_code')]
		for row in self.items:
			if row.item_code not in wo_item:
				frappe.throw(_(f"Item <b>{row.item_code}</b> not in Work Order {self.work_order}. Please add item in work order."))


def validate_additional_cost(self):
	if self.purpose in ['Material Transfer','Material Transfer for Manufacture','Repack','Manufacture'] and self._action == "submit":
		if round(self.value_difference/100,0) != round(self.total_additional_costs/100,0):
			frappe.throw("ValuationError: Value difference between incoming and outgoing amount is higher than additional cost")

def validate_item_packing(self):
	if self.amended_from and self.from_item_packing:
		frappe.throw(_("Please create manufacturing entry from Item Packing"))

def remove_ref_from_item_packing(self):
	if self.from_item_packing and self.purpose in ["Manufacture","Material Receipt"]:
		item_packing_list = frappe.get_list("Item Packing",{'stock_entry':self.name},'name')
		if item_packing_list:
			for row in item_packing_list:
				doc = frappe.get_doc("Item Packing",row)
				doc.db_set('stock_entry','')
				doc.db_set('not_yet_manufactured', 1)

def set_serial_nos(self,work_order):
	previous_se = frappe.db.get_value("Stock Entry", {"work_order": work_order,
			"purpose": "Material Transfer for Manufacture"}, "name")

	for d in self.get('items'):
		transferred_serial_no = frappe.db.get_value("Stock Entry Detail",{"parent": previous_se,
			"item_code": d.item_code}, "serial_no")

		list_serial_no = get_serial_nos(transferred_serial_no)
		serial_no_final = ''
		counter = 0
		for sr_no in list_serial_no:
			if frappe.db.get_value("Serial No",sr_no,'warehouse') == d.s_warehouse:
				serial_no_final += sr_no + "\n"
				counter += 1
				if counter == d.qty:
					break
		
		if serial_no_final:
			d.serial_no = serial_no_final.strip()

@frappe.whitelist()
def check_rate_diff(doctype,docname):
	diff_list = []
	doc = frappe.get_doc(doctype,docname)
	for item in doc.items:
		sle_val_diff,actual_qty = frappe.db.get_value("Stock Ledger Entry",{"voucher_type":doc.doctype,"voucher_no":doc.name,"voucher_detail_no":item.name,"actual_qty":("<",0)},["stock_value_difference","actual_qty"])
		sle_valuation_rate = sle_val_diff / actual_qty
		if item.valuation_rate != sle_valuation_rate:
			diff_list.append(frappe._dict({"idx":item.idx,"item_code":item.item_code,"entry_rate":item.valuation_rate,"ledger_rate":sle_valuation_rate,"rate_diff":item.valuation_rate - sle_valuation_rate}))

	table = """<table class="table table-bordered" style="margin: 0; font-size:90%;">
		<thead>
			<tr>
				<th>Idx</th>
				<th>Item</th>
				<th>Entry Rate</th>
				<th>Ledger Rate</th>
				<th>Rate Diff</th>
			<tr>
		</thead>
	<tbody>"""
	for item in diff_list:
		table += f"""
			<tr>
				<td>{item.idx}</td>
				<td>{item.item_code}</td>
				<td>{item.entry_rate}</td>
				<td>{item.ledger_rate}</td>
				<td>{item.rate_diff}</td>
			</tr>
		"""
	
	table += """
	</tbody></table>
	"""

	frappe.msgprint(
		title = "Items Rate Difference",
		msg = str(table))