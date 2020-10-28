# taxes_and_totals controller override
import frappe
from frappe import _, ValidationError
from frappe.utils import cint, flt, formatdate, format_time


# calculate_taxes_and_totals class method override
def get_current_tax_amount(self, item, tax, item_tax_map):
	tax_rate = self._get_tax_rate(tax, item_tax_map)
	current_tax_amount = 0.0

	if tax.charge_type == "Actual":
		# distribute the tax amount proportionally to each item row
		actual = flt(tax.tax_amount, tax.precision("tax_amount"))
		current_tax_amount = item.net_amount*actual / self.doc.net_total if self.doc.net_total else 0.0

	elif tax.charge_type == "On Net Total":
		if self.doc.authority == "Unauthorized":
			current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount
		else:
			current_tax_amount = (tax_rate / 100.0) * item.net_amount
	elif tax.charge_type == "On Previous Row Amount":
		current_tax_amount = (tax_rate / 100.0) * \
			self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
	elif tax.charge_type == "On Previous Row Total":
		current_tax_amount = (tax_rate / 100.0) * \
			self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item
	elif tax.charge_type == "On Item Quantity":
		current_tax_amount = tax_rate * item.stock_qty

	self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

	return current_tax_amount

def determine_exclusive_rate(self):
	if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
		return

	for item in self.doc.get("items"):
		item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
		cumulated_tax_fraction = 0
		for i, tax in enumerate(self.doc.get("taxes")):
			tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)[0]

			if i==0:
				tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
			else:
				tax.grand_total_fraction_for_current_item = \
					self.doc.get("taxes")[i-1].grand_total_fraction_for_current_item \
					+ tax.tax_fraction_for_current_item

			cumulated_tax_fraction += tax.tax_fraction_for_current_item
		if cumulated_tax_fraction and not self.discount_amount_applied and item.qty:
			# Finbyz Changes for Tax Calculation on Real Rate
			if self.doc.authority == "Unauthorized":
				amount_diff = item.amount - item.discounted_amount
				item.discounted_net_amount = flt((item.amount - amount_diff) / (1 + cumulated_tax_fraction))
				
				try:
					item.discounted_net_rate = flt(item.discounted_net_amount / item.real_qty)
				except:
					item.discounted_net_rate = 0
								
				item.net_amount = item.amount - (item.discounted_amount - item.discounted_net_amount)
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			# Finbyz Changes end here.
			else:
				item.net_amount = flt(item.amount / (1 + cumulated_tax_fraction))
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			item.discount_percentage = flt(item.discount_percentage,
				item.precision("discount_percentage"))

			self._set_in_company_currency(item, ["net_rate", "net_amount"])

def calculate_taxes(self):
	self.doc.rounding_adjustment = 0
	# maintain actual tax rate based on idx
	actual_tax_dict = dict([[tax.idx, flt(tax.tax_amount, tax.precision("tax_amount"))]
		for tax in self.doc.get("taxes") if tax.charge_type == "Actual"])

	for n, item in enumerate(self.doc.get("items")):
		item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
		for i, tax in enumerate(self.doc.get("taxes")):
			# tax_amount represents the amount of tax for the current step
			current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

			# Adjust divisional loss to the last item
			if tax.charge_type == "Actual":
				actual_tax_dict[tax.idx] -= current_tax_amount
				if n == len(self.doc.get("items")) - 1:
					current_tax_amount += actual_tax_dict[tax.idx]

			# accumulate tax amount into tax.tax_amount
			if tax.charge_type != "Actual" and \
				not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
					tax.tax_amount += current_tax_amount

			# store tax_amount for current item as it will be used for
			# charge type = 'On Previous Row Amount'
			tax.tax_amount_for_current_item = current_tax_amount

			# set tax after discount
			tax.tax_amount_after_discount_amount += current_tax_amount

			current_tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(current_tax_amount, tax)

			# note: grand_total_for_current_item contains the contribution of
			# item's amount, previously applied tax and the current tax on that item
			if i==0:
				# Finbyz Changes Start
				if self.doc.authority == "Unauthorized":
					tax.grand_total_for_current_item = flt(item.discounted_net_amount + current_tax_amount)
				# Finbuz Changes End
				else:
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount)
			else:
				tax.grand_total_for_current_item = \
					flt(self.doc.get("taxes")[i-1].grand_total_for_current_item + current_tax_amount)

			# set precision in the last item iteration
			if n == len(self.doc.get("items")) - 1:
				self.round_off_totals(tax)
				self.set_cumulative_total(i, tax)

				self._set_in_company_currency(tax,
					["total", "tax_amount", "tax_amount_after_discount_amount"])

				# adjust Discount Amount loss in last tax iteration
				if i == (len(self.doc.get("taxes")) - 1) and self.discount_amount_applied \
					and self.doc.discount_amount and self.doc.apply_discount_on == "Grand Total":
						self.doc.rounding_adjustment = flt(self.doc.grand_total
							- flt(self.doc.discount_amount) - tax.total,
							self.doc.precision("rounding_adjustment"))
