from __future__ import unicode_literals
from frappe import _
import frappe

def get_data(data):
	data['fieldname'] = 'work_order'
	data['transactions'] = [
		{
			'label': _('Transactions'),
			'items': ['Stock Entry', 'Job Card', 'Pick List', 'Item Packing']
		}
	]
	return data