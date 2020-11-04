import frappe
from erpnext.accounts.doctype.bank_statement_transaction_entry.bank_statement_transaction_entry import get_payments_matching_invoice

def create_payment_entry(self, pe):
	payment = frappe.new_doc("Payment Entry")
	payment.posting_date = pe.transaction_date
	payment.payment_type = "Receive" if pe.party_type == "Customer" else "Pay"
	payment.company = self.company
	payment.party_type = pe.party_type
	payment.party = pe.party
	payment.mode_of_payment = self.mode_of_payment
	payment.paid_to = self.bank_account if pe.party_type == "Customer" else self.payable_account
	payment.paid_from = self.receivable_account if pe.party_type == "Customer" else self.bank_account
	payment.paid_amount = payment.received_amount = abs(pe.amount)
	payment.reference_no = pe.description
	payment.reference_date = pe.transaction_date
	payment.save()
	for inv_entry in self.payment_invoice_items:
		if (pe.description != inv_entry.payment_description or pe.transaction_date != inv_entry.transaction_date): continue
		if (pe.party != inv_entry.party): continue
		reference = payment.append("references", {})
		reference.reference_doctype = inv_entry.invoice_type
		reference.reference_name = inv_entry.invoice
		reference.allocated_amount = inv_entry.allocated_amount
		print ("Adding invoice {0} {1}".format(reference.reference_name, reference.allocated_amount))
	payment.setup_party_account_field()
	payment.set_missing_values()
	#payment.set_exchange_rate()
	#payment.set_amounts()
	#print("Created payment entry {0}".format(payment.as_dict()))
	payment.save()
	return payment

def populate_matching_vouchers(self):
	for entry in self.new_transaction_items:
		if (not entry.party or entry.reference_name): continue
		print("Finding matching voucher for {0}".format(frappe.safe_decode(entry.description)))
		amount = abs(entry.amount)
		invoices = []
		vouchers = get_matching_journal_entries(self.from_date, self.to_date, entry.party, self.bank_account, amount)
		if len(vouchers) == 0: continue
		for voucher in vouchers:
			added = next((entry.invoice for entry in self.payment_invoice_items if entry.invoice == voucher.voucher_no), None)
			if (added):
				print("Found voucher {0}".format(added))
				continue
			print("Adding voucher {0} {1} {2}".format(voucher.voucher_no, voucher.posting_date, voucher.debit))
			ent = self.append('payment_invoice_items', {})
			ent.invoice_date = voucher.posting_date
			ent.invoice_type = "Journal Entry"
			ent.invoice = voucher.voucher_no
			entry.mode_of_payment = self.mode_of_payment
			ent.payment_description = frappe.safe_decode(entry.description)
			ent.allocated_amount = max(voucher.debit, voucher.credit)

			invoices += [ent.invoice_type + "|" + ent.invoice]
			entry.reference_type = "Journal Entry"
			entry.reference_name = ent.invoice
			#entry.account = entry.party
			entry.invoices = ",".join(invoices)
			break

def match_invoice_to_payment(self):
	added_payments = []
	for entry in self.new_transaction_items:
		if (not entry.party or entry.party_type == "Account"): continue
		entry.account = self.receivable_account if entry.party_type == "Customer" else self.payable_account
		amount = abs(entry.amount)
		payment, matching_invoices = None, []
		for inv_entry in self.payment_invoice_items:
			if (inv_entry.payment_description != frappe.safe_decode(entry.description) or inv_entry.transaction_date != entry.transaction_date): continue
			if (inv_entry.party != entry.party): continue
			matching_invoices += [inv_entry.invoice_type + "|" + inv_entry.invoice]
			payment = get_payments_matching_invoice(inv_entry.invoice, entry.amount, entry.transaction_date)
			doc = frappe.get_doc(inv_entry.invoice_type, inv_entry.invoice)
			inv_entry.invoice_date = doc.posting_date
			inv_entry.outstanding_amount = doc.outstanding_amount
			inv_entry.allocated_amount = min(float(doc.outstanding_amount), amount)
			amount -= inv_entry.allocated_amount
			if (amount < 0): break

		amount = abs(entry.amount)
		if (payment is None):
			order_doctype = "Sales Order" if entry.party_type=="Customer" else "Purchase Order"
			from erpnext.controllers.accounts_controller import get_advance_payment_entries
			payment_entries = get_advance_payment_entries(entry.party_type, entry.party, entry.account, order_doctype, against_all_orders=True)
			payment_entries += self.get_matching_payments(entry.party, amount, entry.transaction_date)
			payment = next((payment for payment in payment_entries if payment.amount == amount and payment not in added_payments), None)
			if (payment is None):
				print("Failed to find payments for {0}:{1}".format(entry.party, amount))
				continue
		added_payments += [payment]
		entry.reference_type = payment.reference_type
		entry.reference_name = payment.reference_name
		entry.mode_of_payment = self.mode_of_payment
		entry.outstanding_amount = min(amount, 0)
		if (entry.payment_reference is None):
			entry.payment_reference = frappe.safe_decode(entry.description)
		entry.invoices = ",".join(matching_invoices)
		#print("Matching payment is {0}:{1}".format(entry.reference_type, entry.reference_name))