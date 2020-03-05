# -*- coding: utf-8 -*-
# Copyright (c) 2020, FinByz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class SerialNoGenerator(Document):
	def before_insert(self):
		if self.serial_no_series:
			self.from_value = self.serial_no_series

