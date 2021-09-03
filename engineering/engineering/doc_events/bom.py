import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.get_item_details import get_price_list_rate

def validate(self,method):
	_update_bom_cost(self)

@frappe.whitelist()	
def update_bom_cost(doc,update_parent=True, from_child_bom=False, save=True):
	bom_doc = frappe.get_doc("BOM",doc)
	_update_bom_cost(bom_doc,update_parent=update_parent, from_child_bom=from_child_bom, save=save)

def _update_bom_cost(self,update_parent=False, from_child_bom=False, save=False):
	docitems_type = frappe.get_doc({"doctype":"BOM Item"})
	if self.docstatus == 2:
			return

	existing_bom_cost = self.total_cost

	for d in self.get("items"):
		rate, valuation_rate, last_purchase_rate = get_rm_rate(self,{
			"item_code": d.item_code,
			"bom_no": d.bom_no,
			"qty": d.qty,
			"uom": d.uom,
			"stock_uom": d.stock_uom,
			"conversion_factor": d.conversion_factor,
			"company": self.company,
			"return_three_rate":True
		})

		if rate:
			d.rate = rate
		d.amount = flt(d.rate) * flt(d.qty)
		d.base_rate = flt(d.rate) * flt(self.conversion_rate)
		d.base_amount = flt(d.amount) * flt(self.conversion_rate)
		if valuation_rate:
			d.valuation_rate = valuation_rate
			d.valuation_amount = flt(d.valuation_rate) * flt(d.qty)
		if last_purchase_rate:
			d.last_purchase_rate= last_purchase_rate
			d.last_purchase_amount = flt(d.last_purchase_rate) * flt(d.qty)

		if save:
			d.db_update()

	if self.docstatus == 1:
		self.flags.ignore_validate_update_after_submit = True
		self.calculate_cost()

	cost_calculation(self,save)
	
	if save:
		self.db_update()
	self.update_exploded_items()

	# update parent BOMs
	if self.total_cost != existing_bom_cost and update_parent:
		parent_boms = frappe.db.sql_list("""select distinct parent from `tabBOM Item`
			where bom_no = %s and docstatus=1 and parenttype='BOM'""", self.name)

		for bom in parent_boms:
			frappe.get_doc("BOM", bom).update_cost(from_child_bom=True)

	if not from_child_bom:
		frappe.msgprint(_("Cost Updated"))


def cost_calculation(self,save):
	additional_amount = 0	
	valuation_amount = 0
	last_purchase_amount = 0
	docitems_type = frappe.get_doc({"doctype":"BOM Item"})

	
	for row in self.items:
		row.valuation_amount = flt(row.valuation_rate) * flt(row.qty)
		row.last_purchase_amount = flt(row.last_purchase_rate) * flt(row.qty)
		valuation_amount += flt(row.valuation_rate) * flt(row.qty)
		last_purchase_amount += flt(row.last_purchase_rate) * flt(row.qty)

		if save:
			row.db_update()
			
	additional_amount = sum(flt(d.amount) for d in self.additional_cost)
	self.rmc_valuation_amount = flt(valuation_amount)
	self.rmc_last_purchase_amount = flt(last_purchase_amount)
	# self.db_set('rmc_valuation_amount',flt(valuation_amount))
	# self.db_set('rmc_last_purchase_amount',flt(last_purchase_amount))
	self.additional_amount = additional_amount
	self.total_operational_cost = flt(self.additional_amount)
	self.total_scrap_cost = abs(self.scrap_material_cost)
	# self.db_set('total_operational_cost',flt(self.additional_amount))
	# self.db_set('total_scrap_cost', abs(self.scrap_material_cost))

	self.total_cost = self.raw_material_cost + self.total_operational_cost - flt(self.scrap_material_cost)
	self.total_valuation_cost = self.rmc_valuation_amount + self.total_operational_cost - flt(self.scrap_material_cost)
	self.total_last_purchase_cost = self.rmc_last_purchase_amount + self.total_operational_cost - flt(self.scrap_material_cost)
	# self.db_set('total_cost',self.raw_material_cost + self.total_operational_cost - flt(self.scrap_material_cost))
	# self.db_set('total_valuation_cost',self.rmc_valuation_amount + self.total_operational_cost - flt(self.scrap_material_cost))
	# self.db_set('total_last_purchase_cost',self.rmc_last_purchase_amount + self.total_operational_cost - flt(self.scrap_material_cost))

def get_rm_rate(self, arg):
	"""	Get raw material rate as per selected method, if bom exists takes bom cost """
	rate = 0
	valuation_rate = 0
	last_purchase_rate = 0
	
	if not self.rm_cost_as_per and not arg.get('return_three_rate'):
		self.rm_cost_as_per = "Valuation Rate"

	if arg.get('scrap_items'):
		rate = get_valuation_rate(arg)
	elif arg:
		#Customer Provided parts will have zero rate
		if not frappe.db.get_value('Item', arg["item_code"], 'is_customer_provided_item'):
			if arg.get('bom_no') and self.set_rate_of_sub_assembly_item_based_on_bom:
				rate = flt(get_bom_unitcost(self,arg['bom_no'])) * (arg.get("conversion_factor") or 1)
			else:
				valuation_rate = get_valuation_rate(self,arg) * (arg.get("conversion_factor") or 1)
				last_purchase_rate = get_last_purchase_rate_company_wise(self,arg) * (arg.get("conversion_factor") or 1)

				if not self.buying_price_list:
					frappe.throw(_("Please select Price List"))
				args = frappe._dict({
					"doctype": "BOM",
					"price_list": self.buying_price_list,
					"qty": arg.get("qty") or 1,
					"uom": arg.get("uom") or arg.get("stock_uom"),
					"stock_uom": arg.get("stock_uom"),
					"transaction_type": "buying",
					"company": self.company,
					"currency": self.currency,
					"conversion_rate": 1, # Passed conversion rate as 1 purposefully, as conversion rate is applied at the end of the function
					"conversion_factor": arg.get("conversion_factor") or 1,
					"plc_conversion_rate": 1,
					"ignore_party": True
				})
				item_doc = frappe.get_doc("Item", arg.get("item_code"))
				out = frappe._dict()
				get_price_list_rate(args, item_doc, out)
				rate = out.price_list_rate

				if not rate and not arg.get('return_three_rate'):
					if self.rm_cost_as_per == "Price List":
						frappe.msgprint(_("Price not found for item {0} in price list {1}")
							.format(arg["item_code"], self.buying_price_list), alert=True)
					else:
						frappe.msgprint(_("{0} not found for item {1}")
							.format(self.rm_cost_as_per, arg["item_code"]), alert=True)

				if not rate:
					frappe.msgprint(_("Price not found for item {0} in price list {1}")
						.format(arg["item_code"], self.buying_price_list), alert=True)
				if not valuation_rate:
					frappe.msgprint(_("Valuation rate not found for item {0}")
						.format(arg["item_code"]), alert=True)
				if not last_purchase_rate:
					frappe.msgprint(_("Last purchase rate not found for item {0}")
						.format(arg["item_code"]), alert=True)

	if arg.get('return_three_rate'):	
		return flt(rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1),flt(valuation_rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1),flt(last_purchase_rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1)
	else:
		return flt(rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1)

def get_last_purchase_rate_company_wise(self,arg):
	rate = flt(arg.get('last_purchase_rate'))
		# or frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")) \
		# 	* (arg.get("conversion_factor") or 1)
		# Finbyz Changes: Replaced above line with below query because of get rate from company filter
	if not rate:
		purchase_rate_query = frappe.db.sql("""
			select incoming_rate
			from `tabStock Ledger Entry`
			where is_cancelled = 0 and item_code = '{}' and incoming_rate > 0 and voucher_type in ('Purchase Receipt','Purchase Invoice') and company = '{}'
			order by timestamp(posting_date, posting_time) desc
			limit 1
		""".format(arg['item_code'],arg.get('company') or self.company))
		if purchase_rate_query:
			rate = purchase_rate_query[0][0]
		else:
			rate = frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")
	return rate

def get_valuation_rate(self, args):
	""" Get weighted average of valuation rate from all warehouses """

	total_qty, total_value, valuation_rate = 0.0, 0.0, 0.0
	for d in frappe.db.sql("""select b.actual_qty, b.stock_value from `tabBin` as b
		JOIN `tabWarehouse` as w on w.name = b.warehouse
		where b.item_code=%s and w.company = '{}'""".format(self.company), args['item_code'], as_dict=1):
			total_qty += flt(d.actual_qty)
			total_value += flt(d.stock_value)

	if total_qty:
		valuation_rate =  total_value / total_qty

	if valuation_rate <= 0:
		last_valuation_rate = frappe.db.sql("""select valuation_rate
			from `tabStock Ledger Entry`
			where is_cancelled = 0 and item_code = %s and valuation_rate > 0 and company = '{}'
			order by posting_date desc, posting_time desc, creation desc limit 1""".format(self.company), args['item_code'])

		valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

	if not valuation_rate:
		valuation_rate = frappe.db.get_value("Item", args['item_code'], "valuation_rate")

	return flt(valuation_rate)


def get_bom_unitcost(self, bom_no):
	bom = frappe.db.sql("""select name, base_total_cost/quantity as unit_cost from `tabBOM`
		where is_active = 1 and name = %s and company = '{}'""".format(self.company), bom_no, as_dict=1)
	return bom and bom[0]['unit_cost'] or 0


# override whitelisted method on hooks
@frappe.whitelist()
def enqueue_update_cost():
	frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes!.."))
	frappe.enqueue("engineering.engineering.doc_events.bom.update_cost",timeout=40000)

def update_cost():
	frappe.db.auto_commit_on_many_writes = 1
	from erpnext.manufacturing.doctype.bom.bom import get_boms_in_bottom_up_order

	bom_list = get_boms_in_bottom_up_order()
	for bom in bom_list:
		bom_obj = frappe.get_doc("BOM", bom)
		bom_obj.update_cost(update_parent=False, from_child_bom=True)
		
		update_bom_cost(bom,update_parent=True, from_child_bom=False, save=True)
			
	frappe.db.auto_commit_on_many_writes = 0
