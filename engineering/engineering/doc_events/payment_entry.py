import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details

def validate(self, method):
	if self.references:
		for ref in self.references:
			if ref.reference_doctype == "Sales Invoice":
				self.branch = ref.branch
				break
			if ref.reference_doctype == "Purchase Invoice":
				self.alternate_company = ref.alternate_company
	
	if self.branch:
		self.alternate_company = self.branch
		

def on_submit(self, method):
	"""On Submit Custom Function for Payment Entry"""
	create_payment_entry(self)
	create_payment_enty_branch(self)
	create_payment_entry_pay(self)
	create_payment_entry_receive(self)

def on_update_after_submit(self, method):
	update_payment_entries(self)
	if self.authority == "Unauthorized":
		self.make_gl_entries(cancel=1)
		self.make_gl_entries(cancel=0)

def update_payment_entries(self):
	authority = frappe.db.get_value("Company", self.company, 'authority')
	
	if authority == "Unauthorized" and not self.pe_ref:
		for item in self.references:
			if item.reference_doctype == "Sales Invoice":
				pay_amount_left = real_difference_amount = frappe.db.get_value("Sales Invoice", item.reference_name, 'real_difference_amount')
				allocated_amount = frappe.get_value("Payment Entry References", {'reference_name': item.reference_name, 'docstatus': 1}, "sum(allocated_amount)")
				diff_value = pay_amount_left - allocated_amount
				if diff_value > real_difference_amount:
					frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
				else:
					frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value)
			
			if item.reference_doctype == "Purchase Invoice":
				pay_amount_left = real_difference_amount = frappe.db.get_value("Purchase Invoice", item.reference_name, 'real_difference_amount')
				allocated_amount = frappe.get_value("Payment Entry References", {'reference_name': item.reference_name, 'docstatus': 1}, "sum(allocated_amount)")
				diff_value = pay_amount_left - allocated_amount
				
				if diff_value > real_difference_amount:
					frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
				else:
					frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value)

	if self.pe_ref and not self.get('dont_replicate'):
		payment_doc = frappe.get_doc("Payment Entry", self.pe_ref)
		payment_doc.dont_replicate = 1
		payment_doc_reference_list = [x.reference_name for x in payment_doc.references]

		for idx, row in enumerate(self.references):
			if row.reference_doctype != "Journal Entry" and self.paid_from_account_currency == 'INR' and self.paid_from_account_currency == 'INR':
				ref_field = "pi_ref" if row.reference_doctype == 'Purchase Invoice' else 'si_ref'
				row.against_voucher = frappe.db.get_value(row.reference_doctype, row.reference_name, ref_field)
				row.voucher_detail_no = None
				row.difference_amount = 0
				row.difference_account = None
				if row.against_voucher not in payment_doc_reference_list:
					row.against_voucher_type = row.reference_doctype
					row.grand_total = row.total_amount
					update_reference_in_payment_entry(row, payment_doc)

def create_payment_entry_pay(self):
	def get_payment_entry_pay(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target.party = source.company
			target.company = source.party
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.set_posting_time = 1

			target.payment_type = "Pay"
			target.party_type = "Supplier"
			target.references = []
			target.pe_ref = None

			if target.mode_of_payment:
				target.paid_from = get_bank_cash_account(target.mode_of_payment, target.company)['account']
			else:
				target.paid_from = source.paid_to.replace(source_company_abbr, target_company_abbr)
			party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
			
			target.paid_to = party_details['party_account']
			target.paid_to_account_currency = party_details['party_account_currency']
			target.paid_to_account_balance = party_details['account_balance']

			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "branch_pay_pe_ref")

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {
					"name": "branch_receive_pe_ref",
					"posting_date": "posting_date",
					"posting_time": "posting_time"
				},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"alternate_company",
					"through_company",
					"references",
					"paid_to",
					"paid_from",
					"paid_to",
					"total_allocated_amount",
					"pe_ref",
					"branch_pay_pe_ref",
					"branch_receive_pe_ref",
					"paid_to",
					"paid_from",
					"bank_account",
					"party_bank_account",
					"serial_no",
				},
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	if frappe.db.exists("Company", self.party) and frappe.db.exists("Supplier", self.company):
		if not self.branch_pay_pe_ref and self.payment_type == "Receive":
			pe = get_payment_entry_pay(self.name)
			# frappe.throw(str(pe.paid_from))
			pe.naming_series = 'A' + pe.naming_series
			pe.save()
			pe.submit()

			self.db_set('branch_pay_pe_ref', pe.name)

def create_payment_entry_receive(self):
	def get_payment_entry_receive(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target.party = source.company
			target.company = source.party
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.set_posting_time = 1

			# target.paid_to = source.paid_from.replace(source_company_abbr, target_company_abbr)
			# target.paid_from = source.paid_to.replace(source_company_abbr, target_company_abbr).replace("Creditors", "Debtors")

			target.payment_type = "Receive"
			target.party_type = "Customer"
			target.references = []
			target.pe_ref = None

			if target.mode_of_payment:
				target.paid_to = get_bank_cash_account(target.mode_of_payment, target.company)['account']
			else:
				target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
			party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
			
			target.paid_from = party_details['party_account']
			target.paid_from_account_currency = party_details['party_account_currency']
			target.paid_from_account_balance = party_details['account_balance']

			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "branch_receive_pe_ref")

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {
					"name": "branch_pay_pe_ref",
					"posting_date": "posting_date",
					"posting_time": "posting_time"
				},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"alternate_company",
					"through_company",
					"references",
					"paid_to",
					"paid_from",
					"paid_to",
					"total_allocated_amount",
					"pe_ref",
					"branch_pay_pe_ref",
					"branch_receive_pe_ref",
					"paid_to",
					"paid_from",
					"bank_account",
					"party_bank_account",
					"serial_no"
				},
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	if frappe.db.exists("Company", self.party) and frappe.db.exists("Customer", self.company):
		if not self.branch_receive_pe_ref and self.payment_type == "Pay":
			pe = get_payment_entry_receive(self.name)
			pe.naming_series = 'A' + pe.naming_series
			pe.save()
			pe.submit()

			self.db_set('branch_receive_pe_ref', pe.name)

def create_payment_enty_branch(self):
	def get_payment_entry_pay(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.set_posting_time = 1

			target.payment_type = "Pay"
			target.party_type = "Supplier"
			target.party = source.through_company
			target.references = []
			target.pe_ref = None

			if target.mode_of_payment:
				target.paid_from = get_bank_cash_account(target.mode_of_payment, target.company)['account']
			else:
				target.paid_from = source.paid_to.replace(source_company_abbr, target_company_abbr)
			party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
			target.paid_to = party_details['party_account']
			target.paid_to_account_currency = party_details['party_account_currency']
			target.paid_to_account_balance = party_details['account_balance']

			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "branch_pay_pe_ref")

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {
					"posting_date": "posting_date",
					"posting_time": "posting_time"
				},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"alternate_company",
					"through_company",
					"references",
					"paid_to",
					"paid_from",
					"paid_to",
					"total_allocated_amount",
					"pe_ref",
					"branch_pay_pe_ref",
					"branch_receive_pe_ref",
					"paid_to",
					"paid_from",
					"bank_account",
					"party_bank_account",
					"serial_no"
				},
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	def get_payment_entry_receive(source_name, target_doc=None, ignore_permissions= True):
		def set_missing_values(source, target):
			target.party = source.company
			target.company = source.through_company

			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			# target.paid_from = source.paid_from.replace(source_company_abbr, target_company_abbr)
			# target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)

			target.payment_type = "Receive"
			target.party_type = "Customer"
			target.references = []
			target.pe_ref = ''

			if target.mode_of_payment:
				target.paid_to = get_bank_cash_account(target.mode_of_payment, target.company)['account']
			else:
				target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
			party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
			
			target.paid_from = party_details['party_account']
			target.paid_from_account_currency = party_details['party_account_currency']
			target.paid_from_account_balance = party_details['account_balance']

			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "branch_receive_pe_ref")

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"alternate_company",
					"through_company",
					"references",
					"paid_to",
					"paid_from",
					"paid_to",
					"total_allocated_amount"
					"pe_ref",
					"branch_pay_pe_ref",
					"branch_receive_pe_ref",
					"paid_to",
					"paid_from",
					"bank_account",
					"party_bank_account",
					"serial_no"
				},
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	if self.through_company and self.authority == "Unauthorized" and self.payment_type == "Receive":
		if not frappe.db.exists("Company", self.party):
			pe = get_payment_entry_pay(self.name)
			pe.branch_pe_ref = self.name

			pe.naming_series = 'A' + pe.naming_series

			pe.save()

			pe2 = get_payment_entry_receive(self.name)
			pe2.branch_pe_ref = self.name

			pe2.naming_series = 'A' + pe2.naming_series
			
			pe2.save()

			pe.branch_receive_pe_ref = pe2.name
			pe2.branch_pay_pe_ref = pe.name

			pe.save()
			pe2.save()

			frappe.db.set_value("Payment Entry", self.name, 'branch_pay_pe_ref', pe.name)
			pe.submit()
			pe.db_set('pe_ref', None)


			frappe.db.set_value("Payment Entry", self.name, 'branch_receive_pe_ref', pe2.name)
			pe2.submit()
			pe2.db_set('pe_ref', None)
			self.db_set('branch_pe_ref', None)


def on_cancel(self, method):
	"""On Cancel Custom Function for Payment Entry"""
	cancel_payment_entry(self)
	cancel_all(self)

def cancel_all(self):
	pe_ref = [self.name]

	if self.pe_ref:
		doc = frappe.get_doc("Payment Entry", self.pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.pe_ref]
	
	if self.branch_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.pe_ref, self.branch_pe_ref]
	
	if self.branch_pay_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_pay_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.branch_pay_pe_ref]
	
	if self.branch_receive_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_receive_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.branch_receive_pe_ref]
	
	pe_ref = list(set(pe_ref))

	for pe in pe_ref:
		if pe:
			pe_doc = frappe.get_doc("Payment Entry", pe)

			if pe_doc.docstatus == 1:
				pe_doc.cancel()


def on_trash(self, method):
	"""On Delete Custom Function for Payment Entry"""
	delete_all(self)

def delete_all(self):
	pe_ref = [self.name]

	if self.pe_ref:
		doc = frappe.get_doc("Payment Entry", self.pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.pe_ref]
	
	if self.branch_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.branch_pe_ref]
	
	if self.branch_pay_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_pay_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.branch_pay_pe_ref]
	
	if self.branch_receive_pe_ref:
		doc = frappe.get_doc("Payment Entry", self.branch_receive_pe_ref)
		pe_ref += [doc.pe_ref, doc.branch_pe_ref, doc.branch_pay_pe_ref, doc.branch_receive_pe_ref, self.branch_receive_pe_ref]
	
	pe_ref = list(set(pe_ref))
	# frappe.throw(str(pe_ref))

	for pe in pe_ref:
		if pe:
			frappe.db.set_value("Payment Entry", pe, 'pe_ref', None)
			frappe.db.set_value("Payment Entry", pe, 'branch_pe_ref', None)
			frappe.db.set_value("Payment Entry", pe, 'branch_pay_pe_ref', None)
			frappe.db.set_value("Payment Entry", pe, 'branch_receive_pe_ref', None)

	for pe in pe_ref:
		if pe and pe != self.name:
			if frappe.db.exists("Payment Entry", pe):
				frappe.delete_doc("Payment Entry", pe)

def create_payment_entry(self):
	"""Function to create Payment Entry

	This function is use to create Payment Entry from 
	one company to another company if company is authorized.

	Args:
		self (obj): The submited payment entry object from form
	"""

	def get_payment_entry(source_name, target_doc=None, ignore_permissions= True):
		"""Function to get payment entry"""
		
		def set_missing_values(source, target):
			""""""
			# target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = source.alternate_company
			target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.set_posting_time = 1

			if target.payment_type == "Pay":
				if target.mode_of_payment:
					target.paid_from = get_bank_cash_account(target.mode_of_payment, target.company)['account']
				else:
					target.paid_from = source.paid_to.replace(source_company_abbr, target_company_abbr)
				party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
				
				target.paid_to = party_details['party_account']
				target.paid_to_account_currency = party_details['party_account_currency']
				target.paid_to_account_balance = party_details['account_balance']
			
			elif target.payment_type == "Receive":
				if target.mode_of_payment:
					target.paid_to = get_bank_cash_account(target.mode_of_payment, target.company)['account']
				else:
					target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
				party_details = get_party_details(target.company, target.party_type, target.party, target.posting_date)
				target.paid_from = party_details['party_account']
				target.paid_from_account_currency = party_details['party_account_currency']
				target.paid_from_account_balance = party_details['account_balance']
			else:
				target.paid_from = source.paid_from.replace(source_company_abbr, target_company_abbr)
				target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
			


			if source.deductions:
				for index, i in enumerate(source.deductions):
					target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
					target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)
			
			if self.amended_from:
				target.amended_from = frappe.db.get_value("Payment Entry", self.amended_from, "pe_ref")
			

		def payment_ref(source_doc, target_doc, source_parent):
			reference_name = source_doc.reference_name
			if source_parent.payment_type == 'Pay':
				if source_doc.reference_doctype == 'Purchase Invoice':
					target_doc.reference_name = frappe.db.get_value("Purchase Invoice", reference_name, 'pi_ref')
					target_doc.total_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'outstanding_amount')
					target_doc.allocated_amount = min(target_doc.outstanding_amount - (frappe.db.get_value("Purchase Invoice", target_doc.reference_name, 'pay_amount_left')), source_doc.allocated_amount)

			if source_parent.payment_type == 'Receive':
				if source_doc.reference_doctype == 'Sales Invoice':
					target_doc.reference_name = frappe.db.get_value("Sales Invoice", reference_name, 'si_ref')
					target_doc.total_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'rounded_total') or frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'total')
					target_doc.outstanding_amount = frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'outstanding_amount')
					target_doc.allocated_amount = min(target_doc.outstanding_amount - (frappe.db.get_value("Sales Invoice", target_doc.reference_name, 'pay_amount_left')), source_doc.allocated_amount)

		fields = {
			"Payment Entry": {
				"doctype": "Payment Entry",
				"field_map": {
					"name": "pe_ref",
					"posting_date": "posting_date",
					"posting_time": "posting_time"
				},
				"field_no_map": {
					"party_balance",
					"paid_to_account_balance",
					"status",
					"letter_head",
					"print_heading",
					"bank",
					"bank_account_no",
					"remarks",
					"authority",
					"alternate_company",
					"through_company",
					"paid_to",
					"paid_from",
					"bank_account",
					"party_bank_account",
					"serial_no"
				},
			},
			"Payment Entry Reference": {
				"doctype": "Payment Entry Reference",
				"field_map": {},
				"field_no_map": [
					'through_company',
					'branch'
				],
				"postprocess": payment_ref,
			}
		}

		doclist = get_mapped_doc(
			"Payment Entry",
			source_name,
			fields,
			target_doc,
			set_missing_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
	
	# getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")

	if authority == "Authorized":
		pe = get_payment_entry(self.name)
		pe.naming_series = 'A' + pe.naming_series
		pe.save(ignore_permissions= True)
		self.db_set('pe_ref', pe.name)
		pe.submit()
	
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')
					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					if item.allocated_amount > diff_value:
						frappe.throw("Allocated Amount Cannot be Greater Than Difference Amount {}".format(diff_value))
					else:
						frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value - item.allocated_amount)


# Cancel Invoice on Cancel
def cancel_payment_entry(self):
	# getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")
	
	if authority == "Unauthorized":
		if not self.pe_ref:
			for item in self.references:
				if item.reference_doctype == "Sales Invoice":
					diff_value = frappe.db.get_value("Sales Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Sales Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)
				
				if item.reference_doctype == "Purchase Invoice":
					diff_value = frappe.db.get_value("Purchase Invoice", item.reference_name, 'pay_amount_left')

					frappe.db.set_value("Purchase Invoice", item.reference_name, 'pay_amount_left', diff_value + item.allocated_amount)

def delete_payment_entry(self):
	ref_name = self.pe_ref
	try:
		frappe.db.set_value("Payment Entry", self.name, 'pe_ref', '')    
		frappe.db.set_value("Payment Entry", ref_name, 'pe_ref', '')
		frappe.delete_doc("Payment Entry", ref_name, force = 1, ignore_permissions=True)
	except Exception as e:
		frappe.db.rollback()
		frappe.throw(e)
	else:
		pass
