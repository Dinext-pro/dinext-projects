// === limits.js: recalculatePeriodLimits, setCellStyles ===

// Расчёт лимитов по периодам ISS-2025-01239
function recalculatePeriodLimits(frm, periodType, callback) {
    let periodPositions = [];
    let periods = get_display_periods(frm, periodType);

    Object.values(frm.aggregatedTasks || {}).forEach(task => {
        (task.role_data || []).forEach(roleEntry => {
            let roleName = roleEntry.role || '';

            periods.forEach(period => {
                if (!period.is_past) return;

                let fact = parseFloat(roleEntry[`fact_${period.year}_${period.month}`]) || 0;
                if (fact === 0) return;

                periodPositions.push({
                    name: `${task.value}_${roleName}_${period.year}_${period.month}`,
                    document_name: task.value,
                    project_role: roleName,
                    project: frm.doc.name,
                    status: 'Approved',
                    all_hours: fact,
                    year: period.year,
                    month: period.month
                });
            });
        });
    });

    if (periodPositions.length > 0) {
        frappe.call({
            method: 'calculate_timesheet_limits',
            args: {
                timesheet_name: '',
                positions: periodPositions
            },
            callback: function(r) {
                if (r.message) {
                    frm.periodLimitStatuses = {};
                    r.message.forEach(item => {
                        frm.periodLimitStatuses[item.position] = {
                            status: item.status,
                            pct: item.completion_percentage,
                            limit: item.limit
                        };
                    });
                }
                if (callback) callback();
            }
        });
    } else {
        frm.periodLimitStatuses = {};
        if (callback) callback();
    }
}

function setCellStyles() {
    const tasksHeaderCell = document.querySelector(".work-efforts-table .dt-cell--header-0");
    $(".work-efforts-table .datatable .dt-scrollable").addClass("dt-fit-height");
}
