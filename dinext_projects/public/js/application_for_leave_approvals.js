(function () {
	frappe.provide("dinext_projects.approvals");
	const approvals = dinext_projects.approvals;
	if (approvals.aflApprovalsInstalled) return;
	approvals.aflApprovalsInstalled = true;

	const validateLeaveDates = (frm) => {
		const start = frm.doc.alfrom_date;
		const end = frm.doc.alto_date;
		if (!start || !end) return;
		if (frappe.datetime.get_diff(end, start) < 0) {
			frappe.show_alert(
				{
					message: __("End date cannot be earlier than start date"),
					indicator: "orange",
				},
				5
			);
			frm.set_value("alto_date", start);
		}
	};

	frappe.ui.form.on("Application For Leave", {
		alfrom_date: validateLeaveDates,
		alto_date: validateLeaveDates,
	});
})();
