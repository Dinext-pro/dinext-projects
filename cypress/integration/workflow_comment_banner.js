Cypress.removeAllListeners("uncaught:exception");
const helper = "dinext_common.tests.required_pending_ui";
let fixture;

context("Leave shared approval messages", () => {
	before(() => {
		cy.setCookie("sid", Cypress.env("sid"), { httpOnly: true });
		cy.openDesk("/app");
		cy.call(`${helper}.seed_workflow_comment_leave_cypress`, {})
			.then((res) => { fixture = res.body.message; });
	});
	after(() => {
		cy.setCookie("sid", Cypress.env("sid"), { httpOnly: true });
		cy.openDesk("/app");
		cy.call(`${helper}.cleanup_required_pending_cypress`, {});
	});
	it("uses the shared comments and pending message without the legacy refresh exception", () => {
		cy.login(fixture.viewer, fixture.password);
		cy.openDesk(`/app/application-for-leave/${encodeURIComponent(fixture.leave)}`);
		for (const theme of ["dark", "light"]) {
			cy.window().then((win) => win.frappe.ui.set_theme(theme));
			cy.get(".form-message.dinext-workflow-comments").should("have.length", 1)
				.and("contain", fixture.required).and("contain", fixture.mixed);
			cy.get(".form-message.dinext-pending-approvers").should("have.length", 1);
			cy.get(".form-dashboard-section.dinext-pending-approvers").should("not.exist");
			cy.window().then((win) => win.cur_frm.reload_doc());
		}
		cy.get(".form-message.dinext-workflow-comments").should("have.length", 1);
	});
});
