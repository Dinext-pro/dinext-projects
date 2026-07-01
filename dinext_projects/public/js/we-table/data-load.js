// we-table/data-load.js — load_work_efforts_data, rollup_fact_data
// ISS-2025-01239

let _sum_we_cache = {};

function load_work_efforts_data(frm, periodType, unit, updateRows) {
    // Очистка кэша назначений при загрузке новых данных
    clear_assignments_cache();

    if (frm.last_loaded_project == frm.doc.name && (new Date() - frm.last_loaded_time) < 300000) {
        return;
    }

    frm.work_efforts_dt.freeze();
    console.time("load_work_efforts_data_optimized");

    clearTaskIndexCacheFor(frm.aggregatedTasks);

    frappe.call({
        method: "dinext_projects.dinext_projects.work_efforts_api.get_work_efforts_consolidated_data",
        args: {
            project: frm.doc.name,
            view_options: frm.view_options || "Прогноз и факт"
        },
        freeze_message: __("Загрузка данных о трудозатратах..."),
        callback: function(r) {
            if (r.message) {
                console.timeLog("load_work_efforts_data_optimized", "Данные получены");

                let tasksArray = r.message;
                frm.aggregatedTasks = {};

                tasksArray.forEach(task => {
                    if (task && task.value) {
                        frm.aggregatedTasks[task.value] = task;
                    }
                });

                console.log("Загруженные задачи:", Object.keys(frm.aggregatedTasks));

                _sum_we_cache = {};

                function doContinue() {
                    let table_data = tasksArray;
                    let visibleRows;

                    if (updateRows) {
                        visibleRows = frm.work_efforts_dt.bodyRenderer.visibleRowIndices;
                    }

                    buildWorkloadPeriodsMap(frm).then(() => {
                        console.time("work_efforts_dt.refresh");
                        frm.work_efforts_dt.refresh(table_data);
                        frm.work_efforts_dt.rowmanager.collapseAllNodes();
                        console.timeEnd("work_efforts_dt.refresh");

                        if (visibleRows) {
                            frm.work_efforts_dt.rowmanager.showRows(visibleRows);
                        }

                        frm.work_efforts_dt.unfreeze();

                        setCellStyles();

                        if (typeof render_labour_percentage_chart === 'function') {
                            render_labour_percentage_chart(frm);
                        }

                        if (typeof render_work_efforts_chart === 'function') {
                            render_work_efforts_chart(frm);
                        }

                        syncPlTaskDimensionFromWe(frm);

                        console.timeEnd("load_work_efforts_data_optimized");

                        frm.last_loaded_project = frm.doc.name;
                        frm.last_loaded_time = new Date();
                    });
                }

                recalculatePeriodLimits(frm, periodType, doContinue);
            }
        },
        error: function(err) {
            console.error("Ошибка при загрузке данных:", err);
            frappe.msgprint(__("Ошибка при загрузке данных о трудозатратах"));
            frm.work_efforts_dt.unfreeze();
        }
    });
}

// Свёртка (rollup) фактических данных:
// для каждой задачи суммируются fact_* из дочерних задач с той же ролью.
function rollup_fact_data(aggregatedTasks) {
    let tasksArray = Object.values(aggregatedTasks).sort((a, b) => b.indent - a.indent);
    tasksArray.forEach(child => {
        if (child.parent_task && aggregatedTasks[child.parent_task]) {
            let parent = aggregatedTasks[child.parent_task];
            child.role_data.forEach(childRoleEntry => {
                let role = childRoleEntry.role;
                let parentRoleEntry = parent.role_data.find(r => r.role === role);
                for (let prop in childRoleEntry) {
                    if (prop.startsWith("fact_")) {
                        if (!parentRoleEntry) {
                            parentRoleEntry = { role: role };
                            parent.role_data.push(parentRoleEntry);
                        }
                        if (prop.startsWith("fact_utps")) {
                            if (!parentRoleEntry[prop]) {
                                parentRoleEntry[prop] = [];
                            }
                            parentRoleEntry[prop].push(...(childRoleEntry[prop] || []));
                        } else {
                            let childFact = parseFloat(childRoleEntry[prop]) || 0;
                            if (childFact) {
                                parentRoleEntry[prop] = (parseFloat(parentRoleEntry[prop]) || 0) + childFact;
                            }
                        }
                    }
                }
            });
        }
    });
}

window.load_work_efforts_data = load_work_efforts_data;
window.rollup_fact_data = rollup_fact_data;
