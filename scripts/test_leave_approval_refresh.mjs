import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let handlers;
let exception;
let requests = 0;
let corrected;
const context = {
  dinext_projects: { approvals: {} },
  frappe: {
    provide() {}, boot: { enable_parallel_workflow_approval: true },
    ui: { form: { on(_doctype, value) { handlers = value; } } },
    datetime: { get_diff: () => -1 }, show_alert() {},
    throw(message) { throw new Error(message); },
    xcall: async () => { requests++; return []; },
  },
  __: (text) => text,
};
vm.runInNewContext(fs.readFileSync(new URL("../dinext_projects/public/js/application_for_leave_approvals.js", import.meta.url), "utf8"), context);
const form = {
  doctype: "Application For Leave", doc: { name: "leave", alfrom_date: "2026-11-07", alto_date: "2026-11-06" },
  dashboard: { parent: {} }, is_new: () => false,
  set_value(fieldname, value) { corrected = { fieldname, value }; },
};
const onRejection = (error) => { exception = error; };
process.on("unhandledRejection", onRejection);
handlers.refresh?.(form);
await new Promise(setImmediate);
process.removeListener("unhandledRejection", onRejection);
assert.equal(exception, undefined, "Leave refresh must not dereference the obsolete dashboard.wrapper");
assert.equal(requests, 0, "The shared form handler owns approval message loading");
handlers.alto_date(form);
assert.deepEqual(corrected, { fieldname: "alto_date", value: "2026-11-07" });
for (const field of ["alfrom_hours", "alto_hours"]) {
  for (const value of [-1, "-1,5"]) {
    const values = { alfrom_hours: 0, alto_hours: 1.5, [field]: value };
    assert.throws(() => handlers.validate?.({ doc: values }), /Leave hours cannot be negative/);
  }
}
assert.doesNotThrow(() => handlers.validate?.({ doc: { alfrom_hours: 0, alto_hours: 1.5 } }));
console.log("Leave refresh, date and hours validation regression passed");
