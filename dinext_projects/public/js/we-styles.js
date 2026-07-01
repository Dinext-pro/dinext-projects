// we-styles.js — подключает we-table.css на форме Project (паттерн как PWR)
// ISS-2025-01239

const WE_TABLE_CSS = "/assets/dinext_projects/css/we-table.css";

function applyWorkEffortsStyles() {
	if (document.querySelector(`link[href^="${WE_TABLE_CSS}"]`)) return;

	const link = document.createElement("link");
	link.id = "work-efforts-styles";
	link.rel = "stylesheet";
	link.href = WE_TABLE_CSS;
	document.head.appendChild(link);
}

Object.assign(dinext_projects.work_efforts, { applyWorkEffortsStyles });

$(document).ready(() => dinext_projects.work_efforts.applyWorkEffortsStyles());

if (typeof frappe !== "undefined") {
	frappe.after_ajax(() => dinext_projects.work_efforts.applyWorkEffortsStyles())
}
