/**
 * Client-side UTP row order (localStorage).
 * Key: user. Value: preferred signature order (project + task + role).
 * Survives reload / new timesheet in same browser; not a server source of truth.
 */

const STORAGE_PREFIX = "dinext:ut:row-order:v1:";

/** @param {object} row position or UTP-like */
export function positionOrderSignature(row) {
	if (!row) {
		return "";
	}
	const project = row.project || "";
	const documentType = row.document_type || "Task";
	const documentName = row.document_name || "";
	const projectRole = row.project_role || "";
	if (!project || !documentName) {
		return "";
	}
	return [project, documentType, documentName, projectRole].join("::");
}

function storageUser(frm) {
	return (
		frm?.doc?.timesheet_from ||
		frappe.session?.user ||
		"guest"
	);
}

function storageKey(user) {
	return STORAGE_PREFIX + String(user || "guest");
}

/** @returns {string[]} */
export function loadStoredOrderSignatures(user) {
	try {
		const raw = localStorage.getItem(storageKey(user));
		if (!raw) {
			return [];
		}
		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) {
			return [];
		}
		return parsed.map(String).filter(Boolean);
	} catch (err) {
		console.warn("[UserTimesheet] row-order read failed", err);
		return [];
	}
}

/** @param {string[]} signatures */
export function saveStoredOrderSignatures(user, signatures) {
	if (!Array.isArray(signatures)) {
		return;
	}
	try {
		localStorage.setItem(storageKey(user), JSON.stringify(signatures));
	} catch (err) {
		console.warn("[UserTimesheet] row-order write failed", err);
	}
}

/**
 * Merge current sheet order into stored preference list.
 * Current signatures keep relative order and stay first among known keys;
 * other remembered signatures append after.
 */
export function persistOrderFromRows(frm, rows) {
	const user = storageUser(frm);
	const current = [];
	const seen = new Set();
	for (const row of rows || []) {
		if (row?.rowType && row.rowType !== "position") {
			continue;
		}
		const sig = positionOrderSignature(row);
		if (!sig || seen.has(sig)) {
			continue;
		}
		seen.add(sig);
		current.push(sig);
	}
	if (!current.length) {
		return;
	}
	const prev = loadStoredOrderSignatures(user);
	const rest = prev.filter((sig) => !seen.has(sig));
	saveStoredOrderSignatures(user, [...current, ...rest]);
}

/** Stable sort positions by stored signature order; unknowns keep relative order at end. */
export function sortPositionsByStoredOrder(frm, positions) {
	if (!Array.isArray(positions) || positions.length < 2) {
		return positions || [];
	}
	const order = loadStoredOrderSignatures(storageUser(frm));
	if (!order.length) {
		return positions;
	}
	const rank = new Map(order.map((sig, i) => [sig, i]));
	return positions
		.map((pos, index) => ({ pos, index, rank: rank.get(positionOrderSignature(pos)) }))
		.sort((a, b) => {
			const aKnown = a.rank != null;
			const bKnown = b.rank != null;
			if (aKnown && bKnown && a.rank !== b.rank) {
				return a.rank - b.rank;
			}
			if (aKnown !== bKnown) {
				return aKnown ? -1 : 1;
			}
			return a.index - b.index;
		})
		.map((item) => item.pos);
}

/** Apply stored order to frm.ts_positions (mutates). */
export function applyStoredPositionOrder(frm) {
	frm.ts_positions = sortPositionsByStoredOrder(frm, frm.ts_positions || []);
	return frm.ts_positions;
}

/**
 * After DnD: align domain model with table row order + persist signatures.
 * @returns {boolean} false → core reverts (unused; always ok for localStorage)
 */
export function onTimesheetRowReorder(frm, ctx) {
	const rows = Array.isArray(ctx?.table?.sourceData)
		? ctx.table.sourceData
		: frm.ut?.rows || [];
	const orderedIds = [];
	for (const row of rows) {
		if (row?.rowType === "position" && row.id != null) {
			orderedIds.push(String(row.id));
		}
	}
	const byId = new Map(
		(frm.ts_positions || []).map((p) => [String(p.name), p])
	);
	const next = [];
	for (const id of orderedIds) {
		const pos = byId.get(id);
		if (pos) {
			next.push(pos);
			byId.delete(id);
		}
	}
	for (const pos of byId.values()) {
		next.push(pos);
	}
	frm.ts_positions = next;
	if (frm.ut) {
		frm.ut.rows = rows;
	}
	persistOrderFromRows(frm, rows);
	return true;
}

export function canReorderTimesheetRow(ctx) {
	return ctx?.row?.rowType === "position";
}

export function validateTimesheetRowReorder(ctx) {
	const move = ctx?.move;
	if (!move) {
		return __("Invalid Move");
	}
	const rows = ctx?.table?.sourceData || [];
	const byId = new Map(rows.map((r) => [String(r?.id), r]));
	const dragged = byId.get(String(move.rowId));
	if (!dragged || dragged.rowType !== "position") {
		return __("Only timesheet positions can be moved");
	}
	if (move.targetRowId != null) {
		const target = byId.get(String(move.targetRowId));
		const targetType = target?.rowType;
		if (targetType && targetType !== "position") {
			/* Allow drop before leave block (= end of position list). */
			const parkBeforeLeave =
				move.position === "before" &&
				(targetType === "section" || targetType === "leave");
			if (!parkBeforeLeave) {
				return __("Cannot move rows into the leave block");
			}
		}
	}
	return true;
}
