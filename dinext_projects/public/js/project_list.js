const prev = frappe.listview_settings.Project || {};
const prevFormatters = prev.formatters || {};

frappe.listview_settings.Project = Object.assign({}, prev, {
	formatters: Object.assign({}, prevFormatters, {
		project_type(value) {
			return value ? __(value) : value;
		},
		custom_payment_scheme(value) {
			return value ? __(value) : value;
		},
	}),
});
