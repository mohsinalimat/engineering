from frappe import _

def get_data():
	return {
		'fieldname': 'reference_docname',
		'non_standard_fieldnames': {
			'Serial No': 'box_serial_no'
		},
		'transactions': [
			{	
				'label': _('Stock Entry'),
				'items': ['Stock Entry']
			},

			{	
				'label': _('Serial No'),
				'items': ['Serial No']
			},		
		],		
	}