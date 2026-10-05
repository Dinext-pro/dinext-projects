const method = "dinext_projects.tests.ui_test_helpers";
const bench = "cd /home/Administrator/mybench && /usr/local/bin/bench --site localhost execute";

const CAPTION = "Держим в курсе, согласуем ключевые вещи";

context("Project stakeholder matrix", () => {
	before(() => {
		cy.exec(`${bench} ${method}.seed_stakeholder_matrix`, { timeout: 180000 }).then((result) => {
			const line = result.stdout
				.trim()
				.split("\n")
				.filter((row) => row.startsWith("{"))
				.pop();
			expect(line, result.stdout).to.be.a("string");
			Cypress.env("stakeholder", JSON.parse(line));
		});
	});

	after(() => {
		cy.exec(`${bench} ${method}.cleanup_stakeholder_matrix`, { timeout: 180000 });
	});

	it("places a high-influence low-interest contact in the upper-left quadrant", () => {
		const fixture = Cypress.env("stakeholder");
		cy.login(fixture.user, fixture.password);
		cy.openDesk(`/app/project/${encodeURIComponent(fixture.project)}`);
		cy.get(".stakeholder-matrix-host", { timeout: 120000 }).should("exist");
		cy.window().then((win) => {
			const row = win.cur_frm.doc.custom_contact_list[0];
			win.frappe.model.set_value(row.doctype, row.name, "influence", 8);
			win.frappe.model.set_value(row.doctype, row.name, "interest", 3);
		});
		cy.window().should((win) => {
			const el = win.document.querySelector(".stakeholder-matrix-host");
			expect(el, "matrix host").to.exist;
			const chart = win.echarts.getInstanceByDom(el);
			expect(chart, "chart").to.exist;
			const option = chart.getOption();
			expect(option.title[0].text).to.eq("Матрица стейкхолдеров");
			const captions = (option.series || []).find((series) => series.name === "quadrant-captions");
			expect(captions, "quadrant captions").to.exist;
			const label = (captions.data || []).find((row) => row && row.text === CAPTION);
			expect(label, "upper-left caption").to.exist;
			expect(label.value[0]).to.be.below(5.5);
			expect(label.value[1]).to.be.above(5.5);
			const cards = (option.series || []).find((series) => series.name === "stakeholders");
			expect(cards, "stakeholder cards").to.exist;
			const point = (cards.data || []).find(
				(row) => row && row.influence === 8 && row.interest === 3
			);
			expect(point, "card").to.exist;
			expect(point.value[0]).to.be.below(5.5);
			expect(point.value[1]).to.be.above(5.5);
			expect(point.caption).to.eq(CAPTION);
			const gap = Math.hypot(label.value[0] - point.value[0], label.value[1] - point.value[1]);
			expect(gap, "caption clears the card").to.be.greaterThan(1.2);
		});
	});
});
