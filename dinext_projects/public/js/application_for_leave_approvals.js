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

	const refreshPendingApprovers = async (frm) => {
		if (frm.is_new()) return;
		const selector = ".dinext-pending-approvers";
		frm.dashboard.wrapper.find(selector).remove();
		if (!frappe.boot?.enable_parallel_workflow_approval) return;
		const rows = await frappe
			.xcall("dinext_common.workflow_approval.api.get_pending_approvers", {
				doctype: frm.doctype,
				name: frm.doc.name,
			})
			.catch(() => []);
		if (!rows.length) return;
		const users = [
			...new Set(rows.map((row) => row.approver_name || row.approver)),
		].sort();
		frm.dashboard.wrapper.prepend(
			`<div class="form-dashboard-section dinext-pending-approvers">
				<div class="section-head">${__("Pending approvers")}</div>
				<div class="section-body">${users
					.map((user) => frappe.utils.escape_html(user))
					.join(", ")}</div>
			</div>`
		);
	};

	frappe.ui.form.on("Application For Leave", {
		refresh(frm) {
			refreshPendingApprovers(frm);
		},
		alfrom_date: validateLeaveDates,
		alto_date: validateLeaveDates,
	});
})();
