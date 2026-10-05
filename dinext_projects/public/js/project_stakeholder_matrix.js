/* Stakeholder matrix under Project Contact List. ECharts via DinextCharts. */

const CHARTS_CORE = "/assets/dinext_common/js/charts/dinext-charts-core.js";
const CHART_CSS = "/assets/dinext_projects/css/project_stakeholder_matrix.css";
const CROSS = 5.5;
const SLOT = 0.55;
const GRID = { left: 78, right: 28, top: 64, bottom: 52 };
const HOST_HEIGHT = 480;
const AXIS_SPAN = 10;
const CARD_PX = { width: 92, height: 44 };
const CARD_GAP = 6;

function ensure_charts() {
	const assets = [CHART_CSS];
	if (!(window.DinextCharts && window.DinextCharts.load)) {
		assets.push(CHARTS_CORE);
	}
	return new Promise((resolve, reject) => {
		frappe.require(assets, () => {
			if (window.DinextCharts && window.DinextCharts.load) {
				resolve();
			} else {
				reject(new Error("DinextCharts failed to load"));
			}
		});
	});
}

function desk_token(variableName, property) {
	const probe = document.createElement("span");
	probe.style.position = "absolute";
	probe.style.left = "-9999px";
	probe.style.setProperty(property, `var(${variableName})`);
	document.body.appendChild(probe);
	const value = window.getComputedStyle(probe).getPropertyValue(property);
	probe.remove();
	if (!value || value === "transparent" || value === "rgba(0, 0, 0, 0)") {
		return "";
	}
	return value.trim();
}

function is_score(value) {
	if (value === null || value === undefined || value === "") {
		return false;
	}
	const number = Number(value);
	return Number.isInteger(number) && number >= 1 && number <= 10;
}

function accept_score(cdt, cdn, fieldname) {
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return false;
	}
	if (row._score_clearing) {
		return true;
	}
	const value = row[fieldname];
	if (value === null || value === undefined || value === "") {
		return true;
	}
	if (is_score(value)) {
		return true;
	}
	// Frappe Int shows an empty cell as 0 when the grid row opens. That is empty, not a score.
	if (Number(value) === 0) {
		row._score_clearing = true;
		frappe.model.set_value(cdt, cdn, fieldname, null);
		row._score_clearing = false;
		return true;
	}
	const label = fieldname === "influence" ? __("Influence") : __("Interest");
	row._score_clearing = true;
	frappe.model.set_value(cdt, cdn, fieldname, null);
	row._score_clearing = false;
	frappe.msgprint({
		title: __("Invalid Score"),
		message: __("{0} must be an integer from 1 to 10", [label]),
	});
	return false;
}

function scored_rows(frm) {
	return (frm.doc.custom_contact_list || []).filter(
		(row) => is_score(row.influence) && is_score(row.interest)
	);
}

function contact_names(ids) {
	if (!ids.length) {
		return Promise.resolve({});
	}
	return frappe.db
		.get_list("Contact", {
			fields: ["name", "full_name"],
			filters: { name: ["in", ids] },
			limit: ids.length,
		})
		.then((rows) => {
			const names = {};
			(rows || []).forEach((row) => {
				names[row.name] = row.full_name || row.name;
			});
			return names;
		})
		.catch(() => {
			const names = {};
			ids.forEach((id) => {
				names[id] = id;
			});
			return names;
		});
}

function short_name(name) {
	const text = name || "";
	return text.length > 16 ? `${text.slice(0, 15)}…` : text;
}

function quadrant_caption(influence, interest) {
	const high_influence = Number(influence) >= 6;
	const high_interest = Number(interest) >= 6;
	if (high_influence && !high_interest) {
		return __("Keep informed and agree key points");
	}
	if (high_influence && high_interest) {
		return __("Collaborate actively");
	}
	if (!high_influence && !high_interest) {
		return __("Inform stakeholders");
	}
	return __("Collect data and involve");
}

function clamp(value, min, max) {
	return Math.min(max, Math.max(min, value));
}

function place_cards(rows, names) {
	const groups = new Map();
	rows.forEach((row) => {
		const key = `${Number(row.interest)}:${Number(row.influence)}`;
		if (!groups.has(key)) {
			groups.set(key, []);
		}
		groups.get(key).push(row);
	});

	const placed = [];
	groups.forEach((group) => {
		const base_x = Number(group[0].interest);
		const base_y = Number(group[0].influence);
		const x_min = base_x <= 5 ? 0.8 : 5.7;
		const x_max = base_x <= 5 ? 5.3 : 10.2;
		const y_min = base_y <= 5 ? 0.8 : 5.7;
		const y_max = base_y <= 5 ? 5.3 : 10.2;
		const cols = Math.min(3, group.length);
		group.forEach((row, index) => {
			const col = index % cols;
			const line = Math.floor(index / cols);
			let x = base_x + (col - (cols - 1) / 2) * SLOT;
			let y = base_y;
			if (line > 0) {
				const direction = base_y <= 5 ? 1 : -1;
				y = base_y + direction * line * SLOT;
			}
			const full_name = names[row.contact] || row.contact || "";
			placed.push({
				x: clamp(x, x_min, x_max),
				y: clamp(y, y_min, y_max),
				influence: Number(row.influence),
				interest: Number(row.interest),
				fullName: full_name,
				shortName: short_name(full_name),
				role: row.project_role || "",
				caption: quadrant_caption(row.influence, row.interest),
			});
		});
	});
	return placed;
}

function desk_plate() {
	const host = document.querySelector(".stakeholder-matrix-host");
	let node = host ? host.parentElement : document.body;
	while (node) {
		const bg = window.getComputedStyle(node).backgroundColor;
		if (bg && bg !== "transparent" && bg !== "rgba(0, 0, 0, 0)") {
			return bg;
		}
		node = node.parentElement;
	}
	return desk_token("--bg-color", "background-color") || window.getComputedStyle(document.body).backgroundColor;
}

function plot_scale(hostWidth) {
	const width = hostWidth > 200 ? hostWidth : 768;
	return {
		x: (width - GRID.left - GRID.right) / AXIS_SPAN,
		y: (HOST_HEIGHT - GRID.top - GRID.bottom) / AXIS_SPAN,
	};
}

function host_plot_width(el) {
	const width = el && el.clientWidth;
	if (width > 200) {
		return width;
	}
	const page = document.querySelector(".layout-main-section");
	return (page && page.clientWidth > 200 && page.clientWidth) || 768;
}

function caption_size(text) {
	const lines = caption_lines(text).split("\n");
	const canvas = caption_size.canvas || (caption_size.canvas = document.createElement("canvas"));
	const ctx = canvas.getContext("2d");
	const family = window.getComputedStyle(document.body).fontFamily || "sans-serif";
	ctx.font = `13px ${family}`;
	let width = 0;
	lines.forEach((line) => {
		width = Math.max(width, ctx.measureText(line).width);
	});
	return {
		width: Math.ceil(width) + 8,
		height: lines.length * 16 + 8,
	};
}

function overlap_area(a, b) {
	const width = Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1);
	const height = Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1);
	if (width <= 0 || height <= 0) {
		return 0;
	}
	return width * height;
}

function card_rect(card, scale) {
	const half_x = (CARD_PX.width / 2 + CARD_GAP) / scale.x;
	const half_y = (CARD_PX.height / 2 + CARD_GAP) / scale.y;
	return {
		x1: card.x - half_x,
		y1: card.y - half_y,
		x2: card.x + half_x,
		y2: card.y + half_y,
	};
}

function quadrant_defs() {
	return [
		{
			text: __("Keep informed and agree key points"),
			cx: 3,
			cy: 8,
			x0: 0.5,
			x1: CROSS,
			y0: CROSS,
			y1: 10.5,
		},
		{
			text: __("Collaborate actively"),
			cx: 8,
			cy: 8,
			x0: CROSS,
			x1: 10.5,
			y0: CROSS,
			y1: 10.5,
		},
		{
			text: __("Inform stakeholders"),
			cx: 3,
			cy: 3,
			x0: 0.5,
			x1: CROSS,
			y0: 0.5,
			y1: CROSS,
		},
		{
			text: __("Collect data and involve"),
			cx: 8,
			cy: 3,
			x0: CROSS,
			x1: 10.5,
			y0: 0.5,
			y1: CROSS,
		},
	];
}

function caption_candidates(bounds, center) {
	const points = [];
	if (
		center.x >= bounds.xMin &&
		center.x <= bounds.xMax &&
		center.y >= bounds.yMin &&
		center.y <= bounds.yMax
	) {
		points.push(center);
	}
	const step = 0.25;
	for (let x = bounds.xMin; x <= bounds.xMax + 1e-6; x += step) {
		for (let y = bounds.yMin; y <= bounds.yMax + 1e-6; y += step) {
			points.push({ x, y });
		}
	}
	if (!points.length) {
		points.push(center);
	}
	return points;
}

function place_one_caption(quadrant, cardRects, scale) {
	const size = caption_size(quadrant.text);
	const half_x = size.width / 2 / scale.x;
	const half_y = size.height / 2 / scale.y;
	const bounds = {
		xMin: quadrant.x0 + half_x,
		xMax: quadrant.x1 - half_x,
		yMin: quadrant.y0 + half_y,
		yMax: quadrant.y1 - half_y,
	};
	const center = { x: quadrant.cx, y: quadrant.cy };
	let best = null;
	caption_candidates(bounds, center).forEach((point) => {
		const plate = {
			x1: point.x - half_x,
			y1: point.y - half_y,
			x2: point.x + half_x,
			y2: point.y + half_y,
		};
		let overlap = 0;
		cardRects.forEach((rect) => {
			overlap += overlap_area(plate, rect);
		});
		const dist = (point.x - center.x) ** 2 + (point.y - center.y) ** 2;
		if (
			!best ||
			overlap < best.overlap - 1e-6 ||
			(Math.abs(overlap - best.overlap) < 1e-6 && dist < best.dist)
		) {
			best = { x: point.x, y: point.y, overlap, dist, size };
		}
	});
	return {
		value: [best.x, best.y],
		text: quadrant.text,
		size: best.size,
	};
}

function place_captions(cards, hostWidth) {
	const scale = plot_scale(hostWidth);
	const cardRects = cards.map((card) => card_rect(card, scale));
	return quadrant_defs().map((quadrant) => place_one_caption(quadrant, cardRects, scale));
}

function wrap_line(line) {
	const parts = [];
	let rest = line;
	while (rest.length > 16 && rest.includes(" ")) {
		const mid = Math.floor(rest.length / 2);
		const left = rest.lastIndexOf(" ", mid);
		const right = rest.indexOf(" ", mid + 1);
		let split = -1;
		if (left > 0 && (right < 0 || mid - left <= right - mid)) {
			split = left;
		} else if (right > 0) {
			split = right;
		}
		if (split <= 0) {
			break;
		}
		parts.push(rest.slice(0, split));
		rest = rest.slice(split + 1);
	}
	parts.push(rest);
	return parts;
}

function caption_lines(text) {
	const value = text || "";
	const raw = value.includes(", ") ? value.replace(", ", ",\n").split("\n") : [value];
	const lines = [];
	raw.forEach((line) => {
		wrap_line(line).forEach((part) => lines.push(part));
	});
	return lines.join("\n");
}

function caption_series(points, color, plate) {
	return {
		name: "quadrant-captions",
		type: "scatter",
		silent: true,
		z: 10,
		data: points,
		// ECharts 6 draws a scatter label only when the symbol itself is drawn.
		symbol: "roundRect",
		symbolSize(value, params) {
			const size = params.data && params.data.size;
			return size ? [size.width, size.height] : [140, 40];
		},
		itemStyle: {
			color: plate,
			opacity: 1,
			borderWidth: 0,
		},
		label: {
			show: true,
			position: "inside",
			color,
			fontSize: 13,
			lineHeight: 16,
			formatter: (params) => caption_lines(params.data && params.data.text),
		},
		labelLayout: { hideOverlap: false },
		tooltip: { show: false },
	};
}

function axis(name, color) {
	return {
		type: "value",
		min: 0.5,
		max: 10.5,
		name,
		nameLocation: "middle",
		nameGap: name ? 36 : 28,
		nameTextStyle: { color, fontSize: 13 },
		axisLabel: { show: false },
		axisTick: { show: false },
		splitLine: { show: false },
		axisLine: {
			symbol: ["none", "arrow"],
			lineStyle: { color, width: 1.2 },
		},
	};
}

function build_option(rows, names, hostWidth) {
	const text = desk_token("--text-color", "color") || window.getComputedStyle(document.body).color;
	const cards = place_cards(rows, names);
	const captions = place_captions(cards, hostWidth);
	return {
		animation: false,
		backgroundColor: "transparent",
		title: {
			text: __("Stakeholder Matrix"),
			left: "center",
			top: 4,
			textStyle: { color: text, fontSize: 16, fontWeight: 600 },
		},
		grid: { left: 78, right: 28, top: 64, bottom: 52 },
		tooltip: {
			trigger: "item",
			formatter(params) {
				const point = params.data || {};
				if (point.text && !point.fullName) {
					return "";
				}
				const role = point.role || "—";
				return [
					frappe.utils.escape_html(point.fullName || ""),
					`${__("Project Role")}: ${frappe.utils.escape_html(role)}`,
					`${__("Influence")}: ${point.influence}`,
					`${__("Interest")}: ${point.interest}`,
					frappe.utils.escape_html(point.caption || ""),
				].join("<br>");
			},
		},
		xAxis: axis(__("Interest in the outcome"), text),
		yAxis: Object.assign(axis(__("Influence on the project"), text), { nameGap: 48 }),
		series: [
			{
				name: "stakeholders",
				type: "scatter",
				z: 3,
				data: cards.map((point) => ({
					value: [point.x, point.y],
					fullName: point.fullName,
					shortName: point.shortName,
					role: point.role,
					influence: point.influence,
					interest: point.interest,
					caption: point.caption,
				})),
				symbol: "roundRect",
				symbolSize: [92, 44],
				itemStyle: {
					color: "#FFF4A3",
					borderColor: "#E4D36A",
					borderWidth: 1,
					shadowBlur: 6,
					shadowColor: "rgba(0,0,0,0.12)",
					shadowOffsetY: 2,
				},
				label: {
					show: true,
					position: "inside",
					color: "#333333",
					fontSize: 11,
					width: 80,
					overflow: "truncate",
					formatter: (params) => (params.data && params.data.shortName) || "",
				},
				markLine: {
					silent: true,
					symbol: "none",
					lineStyle: { type: "dashed", color: text, opacity: 0.55 },
					label: { show: false },
					data: [{ xAxis: CROSS }, { yAxis: CROSS }],
				},
			},
			caption_series(captions, text, desk_plate()),
		],
	};
}

function chart_host(frm) {
	const field = frm.fields_dict.custom_stakeholder_matrix;
	if (!field || !field.$wrapper || !field.$wrapper.length) {
		return null;
	}
	// ControlHTML has no .control-input-wrapper; the chart lives on the field wrapper.
	let $host = field.$wrapper.children(".stakeholder-matrix-host");
	if (!$host.length) {
		$host = $('<div class="stakeholder-matrix-host"></div>');
		field.$wrapper.append($host);
	}
	return $host.get(0);
}

function release_chart(frm) {
	if (frm._stakeholder_unbind) {
		frm._stakeholder_unbind();
		frm._stakeholder_unbind = null;
	}
	if (frm._stakeholder_chart && !frm._stakeholder_chart.isDisposed()) {
		frm._stakeholder_chart.dispose();
	}
	frm._stakeholder_chart = null;
}

function render_stakeholder_matrix(frm) {
	if (!chart_host(frm)) {
		return;
	}
	const seq = (frm._stakeholder_seq = (frm._stakeholder_seq || 0) + 1);
	const rows = scored_rows(frm);
	const ids = [...new Set(rows.map((row) => row.contact).filter(Boolean))];
	ensure_charts()
		.then(() => window.DinextCharts.load())
		.then(() => contact_names(ids))
		.then((names) => {
			if (seq !== frm._stakeholder_seq) {
				return;
			}
			const el = chart_host(frm);
			if (!el) {
				return;
			}
			release_chart(frm);
			const width = host_plot_width(el);
			const chart = window.DinextCharts.mount(el, build_option(rows, names, width));
			frm._stakeholder_chart = chart;
			frm._stakeholder_plot_width = width;
			const unbind_resize = window.DinextCharts.bindResize(chart, el);
			const unbind_width = watch_plot_width(frm, el);
			frm._stakeholder_unbind = () => {
				unbind_resize();
				unbind_width();
			};
		})
		.catch(() => {
			frappe.show_alert({
				message: __("Stakeholder matrix could not be drawn"),
				indicator: "orange",
			});
		});
}

function watch_plot_width(frm, el) {
	if (!window.ResizeObserver) {
		return () => {};
	}
	const observer = new ResizeObserver(() => {
		const next = el.clientWidth;
		const used = frm._stakeholder_plot_width || 0;
		if (next > 200 && Math.abs(next - used) > 24) {
			render_stakeholder_matrix(frm);
		}
	});
	observer.observe(el);
	return () => observer.disconnect();
}

function watch_theme() {
	if (window._stakeholder_matrix_theme_watch) {
		return;
	}
	window._stakeholder_matrix_theme_watch = true;
	const observer = new MutationObserver(() => {
		if (cur_frm && cur_frm.doctype === "Project") {
			render_stakeholder_matrix(cur_frm);
		}
	});
	observer.observe(document.documentElement, {
		attributes: true,
		attributeFilter: ["data-theme", "data-theme-mode"],
	});
}

frappe.ui.form.on("Project", {
	refresh(frm) {
		watch_theme();
		render_stakeholder_matrix(frm);
	},
	validate(frm) {
		(frm.doc.custom_contact_list || []).forEach((row) => {
			["influence", "interest"].forEach((fieldname) => {
				if (row[fieldname] === 0) {
					row[fieldname] = null;
				}
			});
		});
	},
	custom_contact_list_add(frm) {
		render_stakeholder_matrix(frm);
	},
	custom_contact_list_remove(frm) {
		render_stakeholder_matrix(frm);
	},
});

frappe.ui.form.on("Project Contact List", {
	influence(frm, cdt, cdn) {
		if (!accept_score(cdt, cdn, "influence")) {
			return;
		}
		render_stakeholder_matrix(frm);
	},
	interest(frm, cdt, cdn) {
		if (!accept_score(cdt, cdn, "interest")) {
			return;
		}
		render_stakeholder_matrix(frm);
	},
	contact(frm) {
		render_stakeholder_matrix(frm);
	},
	project_role(frm) {
		render_stakeholder_matrix(frm);
	},
});
