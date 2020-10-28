frappe.query_reports["Serial No Range"] = {
    "filters":[
        {
			"fieldname":"from",
			"label": __("From"),
			"fieldtype": "Int",
			"reqd":1,
			"width": "40px"
        },
        {
			"fieldname":"to",
			"label": __("To"),
			"fieldtype": "Int",
			"reqd":1,
			"width": "40px"
		},
		{
			"fieldname":"series",
			"label": __("Series"),
			"fieldtype": "Data",
			"reqd":1,
			"width": "40px"
		}
    ]
}
