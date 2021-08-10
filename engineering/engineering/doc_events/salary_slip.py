import frappe
from erpnext.hr.doctype.leave_application.leave_application import get_leave_details

def validate(self,method):
	set_leave_detail(self)

def set_leave_detail(self):
	data = get_leave_details(self.employee,self.start_date or self.posting_date)
	self.leave_detail = []
	for key,value in data['leave_allocation'].items():
		self.append("leave_detail",{
			'leave_type': key,
			'total_leaves': value['total_leaves'],
			'expired_leaves': value['expired_leaves'],
			'leaves_taken': value['leaves_taken'],
			'pending_leaves': value['pending_leaves'],
			'remaining_leaves':value['remaining_leaves']
		})