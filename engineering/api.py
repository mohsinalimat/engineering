import frappe
from frappe import _


def check_sub_string(string, sub_string): 
    """Function to check if string has sub string"""

    return not string.find(sub_string) == -1


def naming_series_name(name, company_series = None):
    """Function to convert naming series name"""
    
    if check_sub_string(name, '.YYYY.'):
        name = name.replace('.YYYY.', '.2020.')
    
    # changing value of fiscal according to current fiscal year 
    if check_sub_string(name, '.fiscal.'):
        current_fiscal = frappe.db.get_value('Global Defaults', None, 'current_fiscal_year')
        fiscal = frappe.db.get_value("Fiscal Year", str(current_fiscal),'fiscal')
        name = name.replace('.fiscal.', str(fiscal))

    # changing value of company series according to company
    if company_series:
        if check_sub_string(name, 'company_series.'):
            name = name.replace('company_series.', str(company_series))
        elif check_sub_string(name, '.company_series.'):
            name = name.replace('.company_series.', str(company_series))

    # removing the hash symbol from naming series
    if check_sub_string(name, ".#"):
        name = name.replace('#', '')
        if name[-1] == '.':
            name = name[:-1]
    
    return name


# all whitelist functions bellow

@frappe.whitelist()
def check_counter_series(name, company_series = None):
    """Function to get series value for naming series"""

    # renaming the name for naming series
    name = naming_series_name(name, company_series)

    # Checking the current series value
    check = frappe.db.get_value('Series', name, 'current', order_by="name")
    
    # returning the incremented value of check for series value
    if check == 0:
        return 1
    elif check == None:
        # if no current value is found for naming series inserting that naming series with current value 0
        frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
        return 1
    else:
        return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1

@frappe.whitelist()
def before_naming(self, method = None):
    """Function for naming the name of naming series"""

    # if from is not ammended and series_value is greater than zero then 
    if not self.amended_from:
        if self.series_value:
            if self.series_value > 0:
                
                # renaming the name for naming series
                name = naming_series_name(self.naming_series, self.company_series)
                
                # Checking the current series value
                check = frappe.db.get_value('Series', name, 'current', order_by="name")
                
                # if no current value is found inserting 0 for current value for this naming series
                if check == 0:
                    pass
                elif not check:
                    frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
                
                # Updating the naming series decremented by 1 for current naming series
                frappe.db.sql(f"update `tabSeries` set current = {int(self.series_value) - 1} where name = '{name}'")

@frappe.whitelist()
def docs_before_naming(self, method = None):
    from erpnext.accounts.utils import get_fiscal_year

    date = self.get("transaction_date") or self.get("posting_date") or getdate()

    fy = get_fiscal_year(date)[0]
    fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

    if fiscal:
        self.fiscal = fiscal
    else:
        fy_years = fy.split("-")
        fiscal = fy_years[0][2:] + "-" + fy_years[1][2:]
        self.fiscal = fiscal