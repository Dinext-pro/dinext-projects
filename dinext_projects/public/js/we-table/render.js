// render.js — render_work_efforts_table, updateTable, frappe.ui.form.on Project
// Part of dinext_projects.work_efforts namespace (we-table/)

applyWorkEffortsStyles();

/**
 * Синхронизация задач WE -> P&L без повторной инъекции (guard от double pass).
 */
function syncPlTaskDimensionFromWe(frm) {
    if (typeof updateTaskDimension !== 'function') return;
    if (!frm.aggregatedBudget || !frm.aggregatedTasks) return;
    const budgetsArr = Object.values(frm.aggregatedBudget);
    const tasksArr = Object.values(frm.aggregatedTasks);
    if (!budgetsArr.length || !tasksArr.length) return;
    if (budgetsArr.some(row => row && row.task)) return;
    updateTaskDimension(frm);
}
dinext_projects.work_efforts.syncPlTaskDimensionFromWe = syncPlTaskDimensionFromWe;

frappe.ui.form.on("Project", {
    refresh: function(frm) {
        render_work_efforts_table(frm);
    }
});

frappe.ui.form.on("Project", {
    onload: function(frm) {
        frm.show_assignments = false;
        render_work_efforts_table(frm);
    }
});

/**
 * Отрисовка таблицы «Трудозатраты»
 */
function render_work_efforts_table(frm) {
    if (frm.show_assignments === undefined) {
        frm.show_assignments = false;
    }

    if (frm.last_loaded_project == frm.doc.name && (new Date() - frm.last_loaded_time) < 300000) {
        console.log("Загружены данные проекта и прошло менее 5 минут..");
        return;
    }

    let wrapper = frm.get_field("custom_work_efforts").$wrapper;
    wrapper.addClass("work_efforts_container");

    wrapper.empty();
    frm.aggregatedTasks = null;
    frm.we_periods = {};

    let controls = $('<div class="work-efforts-controls"></div>').appendTo(wrapper);
    let table_container = $('<div class="work-efforts-table"></div>').appendTo(wrapper);
    let legend_container = $('<div class="work-efforts-legend"></div>').appendTo(wrapper);

    controls.append(`
        <button class="btn btn-default" id="we_save_plan">${__('Сохранить план')}</button>
        <button class="btn btn-default" id="toggle_plan">${__("Показать план")}</button>
        <button class="btn btn-default" id="toggle_delta">${__("Показать Δ")}</button>
    `);

    addViewOptionsControl(frm, controls);

    let selectedPeriodType = "month";
    let selectedUnit = "hours";
    let all_roles = get_project_roles(frm);

    // Добавляем чекбокс "Назначения"
    let checkbox_wrapper = $('<div class="assignments-checkbox-wrapper"></div>').appendTo(controls);

    let assignments_checkbox = frappe.ui.form.make_control({
        parent: checkbox_wrapper,
        df: {
            fieldtype: 'Check',
            fieldname: 'show_assignments',
            label: __("Назначения"),
            onchange: function() {
                frm.show_assignments = this.get_value();

                let newStickyCount = frm.show_assignments ? 5 : 4;
                frm.work_efforts_dt.setStickyColumnsCount(newStickyCount);

                // Используем updateTable вместо refresh для сохранения иерархии
                if (frm.show_assignments && !allAssignmentsLoaded) {
                    load_all_assignments_if_needed(frm).then(() => {
                        updateTable(frm, selectedPeriodType, selectedUnit);
                    });
                } else {
                    updateTable(frm, selectedPeriodType, selectedUnit);
                }
            }
        },
        value: frm.show_assignments,
        only_input: false,
        render_input: true
    });
    assignments_checkbox.refresh();

    // Добавляем кнопку "Проверить" с margin-left: auto
    controls.append(`
        <div class="btn-group">
            <button class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                ${__('Проверить')} <span class="caret"></span>
            </button>
            <ul class="dropdown-menu dropdown-menu-right">
                <li id="check_plan_load">${__('Наличие плановых трудозатрат')}</li>
                <li id="check_workload_overload">${__('Загрузка превышает прогноз трудозатрат')}</li>
            </ul>
        </div>
    `);

    frm.hide_plan = frm.hide_plan || true;
    frm.hide_delta = frm.hide_delta || true;

    controls.find('#we_save_plan').on('click', function() {
        if (!frm.work_efforts_dt.rowmanager.getCheckedRows()?.length) {
            frappe.msgprint(__("Выберите задачи, для которых необходимо сохранить плановые данные."));
        } else {
            frappe.confirm(
                __("Вы уверены, что хотите сохранить выбранные прогнозные / фактические данные как плановые?"),
                () => {
                    save_forecast_as_plan(frm);
                },
                () => {
                    frappe.show_alert(__("Операция отменена"), 3);
                }
            );
        }
    });

    controls.find('#toggle_plan').on('click', function() {
        frm.hide_plan = !frm.hide_plan;
        $(this).text(frm.hide_plan ? __("Показать план") : __("Скрыть план"));
        updateTable(frm, selectedPeriodType, selectedUnit);
        render_work_efforts_chart(frm);
    });

    controls.find('#toggle_delta').on('click', function() {
        frm.hide_delta = !frm.hide_delta;
        $(this).text(frm.hide_delta ? __("Показать Δ") : __("Скрыть Δ"));
        updateTable(frm, selectedPeriodType, selectedUnit);
    });

    controls.find('#check_plan_load').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        check_plan_load_for_percentage_assignments(frm);
    });

    //ISS-2025-02858 + ст.186
    controls.find('#check_workload_overload').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        perform_overload_check(frm);
    });
    //

    // Инициализация таблицы
    function init_table() {
        let columns = get_columns_definition(frm, selectedPeriodType, selectedUnit);
        let stickyCount = frm.show_assignments ? 5 : 4;

        frm.work_efforts_dt = new StickyDataTable(table_container[0], {
            stickyColumnsCount: stickyCount,
            columns: columns,
            data: [],
            inlineFilters: false,
            layout: "fixed",
            logs: true,
            disableReorderColumn: true,
            serialNoColumn: true,
            checkboxColumn: true,
            checkedRowStatus: true,
            dynamicRowHeight: true,
            getDynamicRowHeight: function(instance, index) {
                let data = instance.datamanager.getData(index);
                if (!data || !data.role_data) return 28;

                // Базовая высота: отступы + высота каждой роли (24px)
                let h = 4 + 24 * (data.role_data.length + ((all_roles.length - 1) > data.role_data.length));

                return h;
            },
            showTotalRow: true,
            cellHeight: null,
            treeView: true,
            freezeMessage: __("Идет загрузка данных.."),
            hooks: {
                columnTotal(columnValues, cell) {
                    if (cell.column.id == "total") {
                        let periods = get_display_periods(frm, frm.currentPeriodType || "month");
                        let all_roles = get_project_roles(frm).filter(r => r);

                        let total_plan = 0;
                        let total_actual = 0;

                        periods.forEach(function(period) {
                            let r = calc_we_column_total(frm, all_roles, period, !frm.hide_plan);
                            total_plan += r.plan;
                            total_actual += r.actual;
                        });

                        let delta = total_plan ? (((total_actual - total_plan) / total_plan) * 100).toFixed(1) : 0;

                        return `<div class="work-efforts-group">
                            ${cur_frm.hide_plan ? "" : `<div class="we-group-plan"><span>${total_plan.toFixed(1)}</span></div>`}
                            <div class="we-group-actual"><span class="readonly-fact">${total_actual.toFixed(1)}</span></div>
                            ${cur_frm.hide_delta ? "" : `<div class="we-group-delta"><span>${Number.parseFloat(delta).toFixed(1)}%</span></div>`}
                          </div>`;
                    } else if (cell.colIndex == 0) {
                        return __('Итого');
                    } else if (cell.colIndex > 1) {
                        let parts = cell.column.id.split("_");

                        if (parts.length == 3) {
                            let year = parts[1];
                            let month = parts[2];
                            let periods = get_display_periods(frm, frm.currentPeriodType || "month");
                            let period = periods.find(p => p.year == year && p.month == month);

                            let all_roles = get_project_roles(frm).filter(r => r);

                            let r = calc_we_column_total(frm, all_roles, period, !frm.hide_plan);
                            let total_plan = r.plan;
                            let total_actual = r.actual;

                            let delta = total_plan ? (((total_actual - total_plan) / total_plan) * 100).toFixed(1) : 0;

                            return `<div class="work-efforts-group"
                                data-year="${year}" 
                                data-month="${month}">
                                ${cur_frm.hide_plan ? "" : `<div class="we-group-plan"><span>${total_plan.toFixed(1)}</span></div>`}
                                <div class="we-group-actual"><span class="readonly-fact">${total_actual.toFixed(1)}</span></div>
                                ${cur_frm.hide_delta ? "" : `<div class="we-group-delta"><span>${Number.parseFloat(delta).toFixed(1)}%</span></div>`}
                              </div>`;
                        }
                    }
                    return "";
                }
            }
        });

        load_work_efforts_data(frm, selectedPeriodType, selectedUnit);
    }
    init_table();
    frm.last_loaded_project = frm.doc.name;
    frm.last_loaded_time = new Date();

    // Рендерим легенду
    render_legend(legend_container);
}
dinext_projects.work_efforts.render_work_efforts_table = render_work_efforts_table;

function updateTable(frm, periodType, unit, skipRestore = false) {
    console.log('UPDATE TABLE');

    recalculatePeriodLimits(frm, periodType, function() {
        frm.work_efforts_dt.freeze();
        let visibleRows = frm.work_efforts_dt.bodyRenderer.visibleRowIndices;

        frm.work_efforts_dt.refresh(
            Object.values(frm.aggregatedTasks),
            get_columns_definition(frm, periodType, unit)
        );

        frm.work_efforts_dt.rowmanager.showRows(visibleRows);
        cur_frm.work_efforts_dt.bodyScrollable.dispatchEvent(new CustomEvent('scroll'));
        frm.work_efforts_dt.unfreeze();

        // При внесении прогноза и плана исчезали загрузка и назначения
        // Добавил восстановление карты загрузки и перезагрузку назначений после обновления таблицы
        if (!skipRestore) {
            setTimeout(() => {
                // Восстанавливаем карту загрузки
                buildWorkloadPeriodsMap(frm).then(() => {
                    // Если чекбокс включен - восстанавливаем назначения
                    if (frm.show_assignments) {
                        load_all_assignments_if_needed(frm).then(() => {
                            // Обновляем ТОЛЬКО колонку назначений (не пересоздавая таблицу)
                            frm.work_efforts_dt.refresh(
                                Object.values(frm.aggregatedTasks),
                                get_columns_definition(frm, periodType, unit)
                            );

                            // Фикс от 24.04.2026 --- ПОСЛЕ ОБНОВЛЕНИЯ АВАТАРОВ - СВОРАЧИВАЕМ ВСЕ УЗЛЫ
                            if (frm.work_efforts_dt && frm.work_efforts_dt.rowmanager && frm.work_efforts_dt.rowmanager.collapseAllNodes) {
                                frm.work_efforts_dt.rowmanager.collapseAllNodes();
                            }
                        });
                    }
                });
            }, 100);
        }
    });
}
dinext_projects.work_efforts.updateTable = updateTable;

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
