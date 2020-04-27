
cur_frm.fields_dict.duty_drawback_cost_center.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
cur_frm.fields_dict.duty_drawback_receivable_account.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
cur_frm.fields_dict.duty_drawback_income_account.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};


cur_frm.fields_dict.meis_cost_center.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
cur_frm.fields_dict.meis_income_account.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
cur_frm.fields_dict.meis_receivable_account.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};

cur_frm.fields_dict.job_work_difference_account.get_query = function (doc) {
    return {
        filters: {
            "company": doc.name
        }
    }
};
cur_frm.fields_dict.job_work_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.name
        }
    }
};
cur_frm.fields_dict.job_work_out_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.name
        }
    }
};
frappe.listview_settings['Company'] = {
    onload: function (listview) {
        $(".restricted-list").hide();
    },
    refresh: function (listview) {
        $(".restricted-list").hide();
    }
};