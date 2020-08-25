erpnext.SerialNoBatchSelector = Class.extend({
	init: function(opts, show_dialog) {
		$.extend(this, opts);
		this.show_dialog = show_dialog;
		// frm, item, warehouse_details, has_batch, oldest
		let d = this.frm.doc;
		this.has_serial_no = 1;

		// if (d && d.has_batch_no && (!d.batch_no || this.show_dialog)) this.has_batch = 1;
		// !(this.show_dialog == false) ensures that show_dialog is implictly true, even when undefined
		// if(d && d.has_serial_no && !(this.show_dialog == false)) this.has_serial_no = 1;

		this.setup();
	},

	setup: function() {
        this.item_code = this.frm.doc.item_code;
        this.warehouse = this.frm.doc.jobwork_in_warehouse;
		this.qty = this.frm.doc.qty;
		this.make_dialog();
		this.on_close_dialog();
	},

	make_dialog: function() {
		var me = this;

		this.data = this.oldest ? this.oldest : [];
		let title = "";
		let fields = [
			{
				fieldname: 'item_code',
				read_only: 1,
				fieldtype:'Link',
				options: 'Item',
				label: __('Item Code'),
				default: me.item_code
			},
			{
				fieldname: 'warehouse',
				fieldtype:'Link',
				options: 'Warehouse',
				reqd: 1,
				read_only: 1,
				label: "Warehouse",
				default: me.warehouse,
				onchange: function(e) {
					fields = fields.concat(me.get_serial_no_fields());
				},
				get_query: function() {
					return {
						query: "erpnext.controllers.queries.warehouse_query",
						filters: [
							["Bin", "item_code", "=", me.item_code],
							["Warehouse", "is_group", "=", 0],
							["Warehouse", "company", "=", me.frm.doc.company]
						]
					}
				}
			},
			{fieldtype:'Column Break'},
			{
				fieldname: 'qty',
				fieldtype:'Float',
				label: 'Qty',
				default: me.qty
			},
			{
				fieldname: 'auto_fetch_button',
				fieldtype:'Button',
				label: __('Auto Fetch'),
				description: __('Fetch Serial Numbers based on FIFO'),
				click: () => {
					let qty = this.dialog.fields_dict.qty.get_value();
					let warehouse = this.dialog.fields_dict.warehouse.get_value();
					let numbers = frappe.call({
						method: "erpnext.stock.doctype.serial_no.serial_no.auto_fetch_serial_number",
						args: {
							qty: qty,
							item_code: me.item_code,
							warehouse: warehouse,
							batch_no: null
						}
					});

					numbers.then((data) => {
						let auto_fetched_serial_numbers = data.message;
						let records_length = auto_fetched_serial_numbers.length;
						if (records_length < qty) {
							frappe.msgprint(`Fetched only ${records_length} serial numbers.`);
						}
						let serial_no_list_field = this.dialog.fields_dict.serial_no;
						numbers = auto_fetched_serial_numbers.join('\n');
						serial_no_list_field.set_value(numbers);
					});
				}
			}
		];

		title = __("Select Serial Numbers");
		fields = fields.concat(this.get_serial_no_fields());

		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Insert'), function() {
			me.values = me.dialog.get_values();
			if(me.validate()) {
				frappe.run_serially([
					() => me.update_serial_no_item(),
					() => { refresh_field("qty"); refresh_field("jobwork_in_warehouse"); refresh_field("serial_no");},
					() => me.dialog.hide()
				])
			}
		});

		if(this.show_dialog) {
			let d = this.frm;
			if (this.frm.doc.serial_no) {
				this.dialog.fields_dict.serial_no.set_value(this.frm.doc.serial_no);
			}
		}

		this.dialog.show();
	},

	on_close_dialog: function() {
		this.dialog.get_close_btn().on('click', () => {
			this.on_close;
		});
	},

	validate: function() {
		let values = this.values;
		if(!values.warehouse) {
			frappe.throw(__("Please select a warehouse"));
			return false;
		}
		if(this.has_batch && !this.has_serial_no) {
			if(values.batches.length === 0 || !values.batches) {
				frappe.throw(__("Please select batches for batched item "
					+ values.item_code));
				return false;
			}
			values.batches.map((batch, i) => {
				if(!batch.selected_qty || batch.selected_qty === 0 ) {
					if (!this.show_dialog) {
						frappe.throw(__("Please select quantity on row " + (i+1)));
						return false;
					}
				}
			});
			return true;

		} else {
			let serial_nos = values.serial_no || '';
			if (!serial_nos || !serial_nos.replace(/\s/g, '').length) {
				frappe.throw(__("Please enter serial numbers for serialized item "
					+ values.item_code));
				return false;
			}
			return true;
		}
	},
	update_serial_no_item() {
		// just updates serial no for the item
		let qty = this.dialog.fields_dict.qty.get_value();
		let warehouse = this.dialog.fields_dict.warehouse.get_value();
		let serial_no = this.dialog.fields_dict.serial_no.get_value();
		
		this.frm.set_value('serial_no', serial_no);
		this.frm.set_value('qty', qty);
		this.frm.set_value('jobwork_in_warehouse', warehouse);
	},

	get_serial_no_fields: function() {
		var me = this;
		this.serial_list = [];

		let serial_no_filters = {
			item_code: me.item_code,
			warehouse: me.warehouse,
			delivery_document_no: ""
		}

		return [
			{fieldtype: 'Section Break', label: __('Serial Numbers')},
			{
				fieldtype: 'Link', fieldname: 'serial_no_select', options: 'Serial No',
				label: __('Select to add Serial Number.'),
				get_query: function() {
					return {
						filters: serial_no_filters
					};
				},
				onchange: function(e) {
					if(this.in_local_change) return;
					this.in_local_change = 1;

					let serial_no_list_field = this.layout.fields_dict.serial_no;
					let qty_field = this.layout.fields_dict.qty;

					let new_number = this.get_value();
					let list_value = serial_no_list_field.get_value();
					let new_line = '\n';
					if(!list_value) {
						new_line = '';
					} else {
						me.serial_list = list_value.replace(/\n/g, ' ').match(/\S+/g) || [];
					}

					if(!me.serial_list.includes(new_number)) {
						this.set_new_description('');
						serial_no_list_field.set_value(me.serial_list.join('\n') + new_line + new_number);
						me.serial_list = serial_no_list_field.get_value().replace(/\n/g, ' ').match(/\S+/g) || [];
					} else {
						this.set_new_description(new_number + ' is already selected.');
					}

					qty_field.set_input(me.serial_list.length);
					this.$input.val("");
					this.in_local_change = 0;
				}
			},
			{fieldtype: 'Column Break'},
			{
				fieldname: 'serial_no',
				fieldtype: 'Long Text',
				label: __(me.has_batch && !me.has_serial_no ? 'Selected Batch Numbers' : 'Selected Serial Numbers'),
				onchange: function() {
					me.serial_list = this.get_value()
						.replace(/\n/g, ' ').match(/\S+/g) || [];
					this.layout.fields_dict.qty.set_input(me.serial_list.length);
				}
			}
		];
	}
});