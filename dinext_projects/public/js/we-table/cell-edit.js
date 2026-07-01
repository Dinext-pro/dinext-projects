// === cell-edit.js: updateForecastValue, save_forecast_as_plan, role add/delete, DOM handlers ===

// Обработчик для выбора новой роли из выпадающего списка
$(document).on('change', '.new-role-select', function(e) {
    let newRole = $(this).val();
    if (!newRole) return;

    let task = $(this).data('task');

    let aggregatedTasks = cur_frm.aggregatedTasks || {};

    let taskData = null;
    if (Array.isArray(aggregatedTasks)) {
        taskData = aggregatedTasks.find(t => t && t.value === task);
    } else {
        taskData = aggregatedTasks[task];
    }

    if (taskData) {
        let role_data = taskData.role_data || [];
        let exists = role_data.some(r => r && r.role === newRole);

        if (!exists) {
            frappe.db.get_list("Project Work Efforts", {
                filters: {
                    pwe_project: cur_frm.doc.name,
                    pwe_task: task,
                    pwe_project_role: newRole
                },
                fields: ["name"],
                limit: 1
            }).then(result => {
                if (result && result.length > 0) {
                    return Promise.resolve(result[0]);
                } else {
                    let new_doc = {
                        doctype: "Project Work Efforts",
                        pwe_project: cur_frm.doc.name,
                        pwe_task: task,
                        pwe_project_role: newRole
                    };
                    return frappe.db.insert(new_doc);
                }
            }).then(() => {
                if (!taskData.role_data) {
                    taskData.role_data = [];
                }
                taskData.role_data.push({ role: newRole });

                // ОЧИСТКА КЭША НАЗНАЧЕНИЙ
                clear_assignments_cache();

                if (cur_frm._tasksByParent) {
                    cur_frm._tasksByParent = null;
                }
                clearTaskIndexCacheFor(cur_frm.aggregatedTasks);

                buildWorkloadPeriodsMap(cur_frm).then(() => {
                    if (cur_frm.show_assignments) {
                        load_all_assignments_if_needed(cur_frm).then(() => {
                            updateTable(cur_frm, "month", "hours");
                        });
                    } else {
                        updateTable(cur_frm, "month", "hours");
                    }
                });

                frappe.show_alert({
                    message: __('Роль {0} добавлена', [newRole]),
                    indicator: 'green'
                }, 3);
            }).catch(err => {
                console.error("Ошибка при создании Project Work Efforts:", err);
                frappe.msgprint(__("Ошибка при добавлении роли"));
            });
        } else {
            updateTable(cur_frm, "month", "hours");
        }
    }
});

// Обработчик для удаления роли
$(document).on('click', '.delete-role-btn', function(e) {
    e.stopPropagation();
    let btn = $(this);
    let task = btn.data("task");
    let role = btn.data("role");

    frappe.confirm(
        __("Вы действительно хотите удалить роль {0} для задачи {1}?", [role, task]),
        () => {
            console.log(`=== УДАЛЕНИЕ РОЛИ ===`);
            console.log(`Задача: ${task}, Роль: "${role}"`);

            frappe.db.get_list("Project Work Efforts", {
                filters: {
                    pwe_project: cur_frm.doc.name,
                    pwe_task: task,
                    pwe_project_role: role
                },
                fields: ["name", "pwe_project_role"],
                limit: 10
            }).then(result => {
                console.log(`Найдено PWE для роли "${role}":`, result);

                if (result && result.length > 0) {
                    let deletePromises = result.map(doc => {
                        console.log(`Удаляем PWE: ${doc.name}, роль: ${doc.pwe_project_role}`);
                        return frappe.call({
                            method: 'frappe.client.delete',
                            args: {
                                doctype: "Project Work Efforts",
                                name: doc.name
                            }
                        });
                    });
                    return Promise.all(deletePromises);
                } else {
                    console.warn(`PWE для роли "${role}" не найден!`);

                    return frappe.db.get_list("Project Work Efforts", {
                        filters: {
                            pwe_project: cur_frm.doc.name,
                            pwe_task: task
                        },
                        fields: ["name", "pwe_project_role"],
                        limit: 100
                    }).then(allDocs => {
                        console.log(`Все PWE для задачи ${task}:`, allDocs);
                        return Promise.resolve();
                    });
                }
            }).then(() => {
                console.log(`=== ОБНОВЛЕНИЕ ЛОКАЛЬНЫХ ДАННЫХ ===`);

                let aggregatedTasks = cur_frm.aggregatedTasks || [];
                let taskData = null;

                if (Array.isArray(aggregatedTasks)) {
                    taskData = aggregatedTasks.find(t => t && t.value === task);
                } else {
                    taskData = aggregatedTasks[task];
                }

                if (taskData && taskData.role_data) {
                    console.log(`Роли до удаления:`, taskData.role_data.map(r => r.role));
                    taskData.role_data = taskData.role_data.filter(r => r.role !== role);
                    console.log(`Роли после удаления:`, taskData.role_data.map(r => r.role));
                } else {
                    console.warn(`taskData или role_data не найдены!`);
                }

                // ОЧИСТКА КЭША НАЗНАЧЕНИЙ
                clear_assignments_cache();

                if (cur_frm._tasksByParent) {
                    cur_frm._tasksByParent = null;
                }
                clearTaskIndexCacheFor(cur_frm.aggregatedTasks);

                console.log(`=== ОБНОВЛЕНИЕ ТАБЛИЦЫ ===`);

                buildWorkloadPeriodsMap(cur_frm).then(() => {
                    if (cur_frm.show_assignments) {
                        load_all_assignments_if_needed(cur_frm).then(() => {
                            updateTable(cur_frm, "month", "hours");
                        });
                    } else {
                        updateTable(cur_frm, "month", "hours");
                    }
                });

                frappe.show_alert({
                    message: __('Роль удалена'),
                    indicator: 'green'
                }, 3);
            }).catch(err => {
                console.error("Ошибка при удалении роли:", err);
                frappe.msgprint(__("Ошибка при удалении роли"));
            });
        }
    );
});

// При клике по значению "факт/прогноз" (если редактирование разрешено)
$(document).on('click', '.we-group-actual .editable-forecast', function(e) {
    // Если уже в режиме редактирования, не обрабатываем повторный клик
    if ($(this).find('input').length > 0) return;

    let $span = $(this);
    let currentValue = $span.text().trim();

    let $input = $(`<input type="number" min="0" class="we-edit-input">`)
        .val(currentValue)
        .data('original-value', currentValue);

    $span.html($input);
    $input.focus();
});

/* Функция расчёта суммы прогнозных трудозатрат у дочерних задач */
function get_child_forecast_sum(taskId, role, period, aggregatedTasks) {
    let sum = 0;
    Object.values(aggregatedTasks).forEach(child => {
        if (child.parent_task === taskId) {
            let childRoleEntry = (child.role_data || []).find(r => r.role === role);
            let forecastKey = `forecast_${period.year}_${period.month}`;
            let childForecast = childRoleEntry ? parseFloat(childRoleEntry[forecastKey]) || 0 : 0;
            if (childForecast > 0) {
                sum += childForecast;
            } else {
                sum += get_child_forecast_sum(child.value, role, period, aggregatedTasks);
            }
        }
    });
    return sum;
}

/* Функция для определения максимального допустимого значения в дочерней задаче */
function get_parent_forecast_limit(taskId, role, period, aggregatedTasks) {
    let currentTask = aggregatedTasks[taskId];
    let excluded = [];
    while (currentTask && currentTask.parent_task) {
        excluded.push(currentTask.value);
        let parent = aggregatedTasks[currentTask.parent_task];
        if (parent) {
            let parentRoleEntry = (parent.role_data || []).find(r => r.role === role);
            let forecastKey = `forecast_${period.year}_${period.month}`;
            let parentForecast = parentRoleEntry ? parseFloat(parentRoleEntry[forecastKey]) || 0 : 0;
            if (parentForecast > 0) {
                let siblingsSum = get_child_forecast_sum(
                    parent.value,
                    role,
                    period,
                    Object.values(aggregatedTasks).filter(function(el) { return excluded.indexOf(el.value) < 0; })
                );
                let maxAllowed = parentForecast - siblingsSum;
                return maxAllowed;
            }
        }
        currentTask = parent;
    }
    return null;
}

// При потере фокуса input – сохраняем значение
$(document).on('blur', '.we-edit-input', function(e) {
    let $input = $(this);
    let new_value = parseFloat($input.val());

    let original_value = $input.data('original-value');
    if (new_value == original_value) {
        $input.parent().text(original_value);
        return;
    }

    // Пробуем найти данные через новую структуру
    let $container = $input.closest('.we-columns-container');
    let $roleValue = $input.closest('.we-role-value');
    let year = $container.data('year');
    let month = $container.data('month');
    let task = $container.data('task');
    let role = $roleValue.data('role');

    // Если не нашли — пробуем старую структуру
    if (!task) {
        let $group = $input.closest('.work-efforts-group');
        year = $group.data('year');
        month = $group.data('month');
        task = $group.data('task');
        role = $group.data('role');
    }

    let period = { year: year, month: month };

    let aggregatedTasks = cur_frm.aggregatedTasks || {};

    let isParent = Object.values(aggregatedTasks).some(t => t.parent_task === task);
    if (isParent) {
        let childrenSum = get_child_forecast_sum(task, role, period, aggregatedTasks);
        if (new_value < childrenSum) {
            frappe.msgprint(__("Значение не может быть меньше суммы трудозатрат дочерних задач (" + childrenSum + ")"));
            $input.addClass("error");
            return;
        }
    }

    let parentLimit = get_parent_forecast_limit(task, role, period, aggregatedTasks);
    if (parentLimit !== null && (new_value > parentLimit)) {
        frappe.msgprint(__("Значение трудозатрат не может превышать " + parentLimit + " (ограничение родительской задачи)"));
        $input.addClass("error");
        return;
    }

    $input.parent().text(new_value || 0);
    updateForecastValue(task, role, year, month, new_value);
});

/* Пример функции обновления прогнозного значения (согласно ранее реализованной логике) */
function updateForecastValue(task, role, year, month, new_value) {
    frappe.db.get_list("Project Work Efforts", {
        filters: {
            pwe_project: cur_frm.doc.name,
            pwe_task: task,
            pwe_project_role: role
        },
        fields: ["name"],
        limit: 1
    }).then(result => {
        if (result && result.length > 0) {
            return frappe.db.get_doc("Project Work Efforts", result[0].name);
        } else {
            let new_doc = {
                doctype: "Project Work Efforts",
                pwe_project: cur_frm.doc.name,
                pwe_task: task,
                pwe_project_role: role
            };
            return frappe.db.insert(new_doc);
        }
    }).then(doc => {
        let existRow = doc.pwe_amount.find(row => row.pwea_year == year && row.pwea_month == month);
        if (!existRow) {
            let newRow = frappe.model.add_child(doc, "Project Work Efforts Amount", "pwe_amount");
            newRow.pwea_year = year;
            newRow.pwea_month = month;
            newRow.pwea_expected = new_value;
        } else {
            existRow.pwea_expected = new_value;
        }
        return frappe.call({
            method: 'frappe.client.save',
            args: { doc: doc }
        });
    }).then(result => {
        frappe.show_alert({
            message: __('Данные успешно обновлены'),
            indicator: 'green'
        }, 5);

        // ОЧИСТКА КЭША НАЗНАЧЕНИЙ
        clear_assignments_cache();

        let aggregatedTasks = cur_frm.aggregatedTasks || [];
        let taskData = null;

        if (Array.isArray(aggregatedTasks)) {
            taskData = aggregatedTasks.find(t => t && t.value === task);
        } else {
            taskData = aggregatedTasks[task];
        }

        if (taskData && taskData.role_data) {
            let roleEntry = taskData.role_data.find(r => r.role === role);
            if (roleEntry) {
                roleEntry[`forecast_${year}_${month}`] = new_value;
            } else {
                taskData.role_data.push({
                    role: role,
                    [`forecast_${year}_${month}`]: new_value
                });
            }
        }

        clearTaskIndexCacheFor(cur_frm.aggregatedTasks);
        buildWorkloadPeriodsMap(cur_frm).then(() => {
            updateTable(cur_frm, "month", "hours");
        });

        render_work_efforts_chart(cur_frm, false);
    }).catch(err => {
        frappe.msgprint(__("Ошибка при обновлении прогноза"));
        console.error(err);
    });
}

function save_forecast_as_plan(frm) {
    let periods = get_display_periods(frm, "month");
    let checkedRows = frm.work_efforts_dt.rowmanager.getCheckedRows();

    let data = [];
    let hasChanges = false;

    for (let i = 0; i < checkedRows.length; i++) {
        let taskObj = frm.work_efforts_dt.datamanager.getData(checkedRows[i]);
        let task = taskObj.value;

        if (taskObj.role_data && Array.isArray(taskObj.role_data)) {
            taskObj.role_data.forEach(roleEntry => {
                let role = roleEntry.role || "";

                periods.forEach(period => {
                    let new_plan_value = 0;
                    let current_plan = parseFloat(roleEntry[`plan_${period.year}_${period.month}`]) || 0;

                    if (period.is_past) {
                        let factKey = `fact_${period.year}_${period.month}`;
                        new_plan_value = parseFloat(roleEntry[factKey]) || 0;
                    } else {
                        let forecastKey = `forecast_${period.year}_${period.month}`;
                        new_plan_value = parseFloat(roleEntry[forecastKey]) || 0;
                    }

                    if (new_plan_value !== current_plan && (new_plan_value > 0 || current_plan > 0)) {
                        hasChanges = true;
                        data.push({
                            task: task,
                            role: role,
                            year: period.year,
                            month: period.month,
                            plan_value: new_plan_value,
                            current_plan: current_plan
                        });
                    }
                });
            });
        }
    }

    if (!hasChanges) {
        frappe.msgprint(__("Нет изменений для сохранения."));
        return;
    }

    if (data.length === 0) {
        frappe.msgprint(__("Нет данных для сохранения."));
        return;
    }

    frappe.call({
        method: "save_forecast_as_plan",
        args: {
            project: frm.doc.name,
            data: JSON.stringify(data)
        },
        freeze: true,
        freeze_message: __("Сохранение данных..."),
        callback: function(r) {
            if (!r.exc) {
                frappe.show_alert(__("Данные успешно сохранены как план"), 5);

                // ОЧИСТКА КЭША НАЗНАЧЕНИЙ
                clear_assignments_cache();

                frm.last_loaded_time = null;
                frm.last_loaded_project = null;

                clearTaskIndexCacheFor(frm.aggregatedTasks);

                // ОЧИСТКА ПОДСВЕТКИ - удаляем карту проблем
                frm._missingPlanMap = {};
                frm._missingPlanPeriodsMap = {};

                load_work_efforts_data(frm, "month", "hours", true);

                if (typeof load_and_render_project_dashboard === 'function') {
                    load_and_render_project_dashboard(frm);
                }
            }
        }
    });
}

// При двойном клике по значению "факт"
// https://erp.dinord.ru/app/issue/ISS-2025-01237
$(document).on('dblclick', '.we-group-actual:not(.zero):has(.readonly-fact)', function(e) {
    let $actual = $(this);

    let $group = $actual.closest('.work-efforts-group');
    let year = $group.data('year');
    let month = $group.data('month');
    let task = $group.data('task');
    let role = $group.data('role');
    let utps = [];

    if (typeof task === 'undefined' || typeof role === 'undefined') {
        let periods = get_display_periods(cur_frm, "month");
        let period = periods.find(period => period.year == year && period.month == month);

        if (period.is_past) {
            Object.values(cur_frm.aggregatedTasks).forEach(task => {
                (task.role_data || []).forEach(roleEntry => {
                    let factUTPs = `fact_utps_${year}_${flt(month)}`;
                    let monthUTPS = roleEntry[factUTPs];
                    if (monthUTPS) {
                        utps.push(...monthUTPS);
                    }
                });
            });
        }
    } else {
        let roleEntry = cur_frm.aggregatedTasks[task]?.role_data?.find(r => r.role === role);

        if (roleEntry) {
            if (typeof year === 'undefined' || typeof month === 'undefined') {
                let periods = get_display_periods(cur_frm, "month");
                periods.forEach(period => {
                    if (period.is_past) {
                        let factUTPs = `fact_utps_${period.year}_${period.month}`;
                        let monthUTPS = roleEntry[factUTPs];
                        if (monthUTPS) {
                            utps.push(...monthUTPS);
                        }
                    }
                });
            } else {
                let factUTPs = `fact_utps_${year}_${flt(month)}`;
                utps = roleEntry[factUTPs];
            }
        }
    }

    if (utps && utps.length) {
        frappe.route_options = {
            name: ["in", utps]
        };
        frappe.set_route('list', 'User Timesheet Position');
    }
});

// Обработчик клика на строку назначений
$(document).on('click', '.assignment-row', function(e) {
    e.stopPropagation();

    let task_id = $(this).data('task');
    if (!task_id) {
        let $row = $(this).closest('.dt-row');
        let rowIndex = $row.data('row-index');
        if (rowIndex !== undefined) {
            let rowData = cur_frm.work_efforts_dt.datamanager.getData(rowIndex);
            if (rowData && rowData.value) {
                task_id = rowData.value;
            }
        }
    }

    if (!task_id) return;

    let task_data = cur_frm.aggregatedTasks[task_id];
    if (!task_data) return;

    let task = {
        name: task_id,
        project: cur_frm.doc.name,
        subject: task_data.subject,
        exp_start_date: task_data.exp_start_date,
        exp_end_date: task_data.exp_end_date
    };

    if (typeof start_pwa_dialog === 'function') {
        start_pwa_dialog(function(pwas) {
            clear_assignments_cache();

            load_all_assignments_if_needed(cur_frm).then(() => {
                updateTable(cur_frm, "month", "hours");

                setTimeout(() => {
                    check_plan_load_for_percentage_assignments(cur_frm);
                }, 300);
            });

            frappe.show_alert({
                message: __('Назначения обновлены'),
                indicator: 'green'
            }, 3);
        }, task);
    } else {
        frappe.msgprint(__("Функция назначений недоступна"));
    }
});

// ========== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ СТРУКТУРЫ С КОЛОНКАМИ ==========

// Клик для редактирования прогноза (новая структура)
$(document).on('click', '.we-role-value .editable-forecast', function(e) {
    if ($(this).find('input').length > 0) return;
    let $span = $(this);
    let currentValue = $span.text().trim();
    let $input = $(`<input type="number" min="0" class="we-edit-input">`)
        .val(currentValue)
        .data('original-value', currentValue);
    $span.html($input);
    $input.focus();
});

// Двойной клик по факту (новая структура)
$(document).on('dblclick', '.we-role-value:not(.zero):has(.readonly-fact)', function(e) {
    let $actual = $(this);
    let $container = $actual.closest('.we-columns-container');
    let year = $container.data('year');
    let month = $container.data('month');
    let task = $container.data('task');
    let role = $actual.data('role');
    let utps = [];

    if (typeof task === 'undefined' || typeof role === 'undefined') {
        let periods = get_display_periods(cur_frm, "month");
        let period = periods.find(p => p.year == year && p.month == month);
        if (period && period.is_past) {
            Object.values(cur_frm.aggregatedTasks).forEach(t => {
                (t.role_data || []).forEach(roleEntry => {
                    let factUTPs = `fact_utps_${year}_${flt(month)}`;
                    let monthUTPS = roleEntry[factUTPs];
                    if (monthUTPS) utps.push(...monthUTPS);
                });
            });
        }
    } else {
        let roleEntry = cur_frm.aggregatedTasks[task]?.role_data?.find(r => r.role === role);
        if (roleEntry) {
            let factUTPs = `fact_utps_${year}_${flt(month)}`;
            let monthUTPS = roleEntry[factUTPs];
            if (monthUTPS) utps.push(...monthUTPS);
        }
    }

    if (utps && utps.length) {
        frappe.route_options = { name: ["in", utps] };
        frappe.set_route('list', 'User Timesheet Position');
    }
});
