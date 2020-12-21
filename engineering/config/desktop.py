# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "Engineering",
			"category": "Modules",
			"label": _("Engineering"),
			"color": "#1abc9c",
			"icon": "icon finbyz-engineering",
			"type": "module",
			"onboard_present": 1
		}
	]
