// === data-load.js: load_work_efforts_data, rollup_fact_data, calc_we_column_total, cache ===

let _sum_we_cache = {};
let _columnTotalCache = {};

function calc_we_column_total_optimized(frm, roles, period, calc_plan = true, calc_fact = false) {
    const cacheKey = `total_${period.year}_${period.month}_${calc_plan}_${calc_fact}`;

    if (_columnTotalCache[cacheKey] !== undefined) {
        return _columnTotalCache[cacheKey];
    }

    let plan = 0;
    let actual = 0;

    if (!frm.aggregatedTasks) {
        return { plan: 0, actual: 0 };
    }

    const tasks = Object.values(frm.aggregatedTasks);
    const filteredRoles = roles.filter(r => r && r.trim());

    if (!frm._tasksByParent) {
        frm._tasksByParent = {};
        tasks.forEach(task => {
            const parent = task.parent_task || '';
            if (!frm._tasksByParent[parent]) {
                frm._tasksByParent[parent] = [];
            }
            frm._tasksByParent[parent].push(task);
        });
    }

    const getChildSum = (() => {
        const childSumCache = {};

        return function(taskId, role, periodKey, valueType = "forecast") {
            const cacheKey = `child_${taskId}_${role}_${periodKey}_${valueType}`;

            if (childSumCache[cacheKey] !== undefined) {
                return childSumCache[cacheKey];
            }

            let sum = 0;
            const children = frm._tasksByParent[taskId] || [];

            for (let i = 0; i < children.length; i++) {
                const child = children[i];
                const roleEntry = child.role_data?.find(r => r.role === role);

                if (roleEntry) {
                    const key = `${valueType}_${periodKey}`;
                    const value = parseFloat(roleEntry[key]) || 0;

                    if (value > 0) {
                        sum += value;
                    } else {
                        sum += getChildSum(child.value, role, periodKey, valueType);
                    }
                }
            }

            childSumCache[cacheKey] = sum;
            return sum;
        };
    })();

    const periodKey = `${period.year}_${period.month}`;
    const valueKey = (period.is_past || calc_fact) ? "fact" : "forecast";

    for (const role of filteredRoles) {
        let rolePlan = 0;
        let roleActual = 0;

        const rootTasks = tasks.filter(t => !t.parent_task);

        for (const root of rootTasks) {
            const roleEntry = root.role_data?.find(r => r.role === role);

            if (calc_plan) {
                let planSum = roleEntry ? parseFloat(roleEntry[`plan_${periodKey}`]) || 0 : 0;
                if (!planSum) {
                    planSum = getChildSum(root.value, role, periodKey, "plan");
                }
                rolePlan += planSum;
            }

            let actualSum = roleEntry ? parseFloat(roleEntry[`${valueKey}_${periodKey}`]) || 0 : 0;
            if (!actualSum) {
                actualSum = getChildSum(root.value, role, periodKey, valueKey);
            }
            roleActual += actualSum;
        }

        plan += rolePlan;
        actual += roleActual;
    }

    const result = { plan, actual };
    _columnTotalCache[cacheKey] = result;

    return result;
}

function calc_we_column_total(frm, roles, period, calc_plan = true, calc_fact = false) {
    return calc_we_column_total_optimized(frm, roles, period, calc_plan, calc_fact);
}

function clearTaskIndexCacheFor(tasks) {
    _sum_we_cache = {};
    _columnTotalCache = {};
    if (cur_frm) {
        cur_frm._tasksByParent = null;
    }
}

function load_work_efforts_data(frm, periodType, unit, updateRows) {
    // ОЧИСТКА КЭША ПРИ ЗАГРУЗКЕ НОВЫХ ДАННЫХ
    clear_assignments_cache();

    if (frm.last_loaded_project == frm.doc.name && (new Date() - frm.last_loaded_time) < 300000) {
        console.log("Используем кэшированные данные проекта (прошло менее 5 минут)");
        return;
    }

    frm.work_efforts_dt.freeze();
    console.time("load_work_efforts_data_optimized");

    clearTaskIndexCacheFor(frm.aggregatedTasks);

    frappe.call({
        method: "get_work_efforts_consolidated_data",
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

                // === НОВЫЙ БЛОК: Расчёт лимитов по периодам ISS-2025-01239 ===
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
                // === КОНЕЦ БЛОКА ===
            }
        },
        error: function(err) {
            console.error("Ошибка при загрузке данных:", err);
            frappe.msgprint(__("Ошибка при загрузке данных о трудозатратах"));
            frm.work_efforts_dt.unfreeze();
        }
    });
}

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
