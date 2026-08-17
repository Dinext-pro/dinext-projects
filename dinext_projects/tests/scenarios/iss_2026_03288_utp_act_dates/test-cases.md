# ISS-2026-03288 UTP → Task act_* (слой 3)

Порт runnable-кейсов ISS-2025-02606 TC-01…05, TC-08…10, TC-24. Новые кейсы не добавлялись.

- issue: `ISS-2026-03288` (источник кейсов: `ISS-2025-02606`)
- site: `dev.dinext.localhost`
- owner_app: `dinext_projects`
- dependent_apps:
  - `erpnext`
  - `dinext_timesheets` (UTP rollup / `status_rollup`)
  - `dinext_project_tasks_gantt` (live-site: `Task.save()` из rollup нормализует `exp_*` слоем 2)
- primary_surface: `Python`
- secondary_surfaces: []
- scenario_dir: `frappe-bench/apps/dinext_projects/dinext_projects/tests/scenarios/iss_2026_03288_utp_act_dates`
- data_helper: `data_setup.py`
- source_of_truth:
  - `dinext_timesheets/dinext_timesheets/user_timesheet/events/status_rollup.py`
  - `dinext_timesheets/hooks.py` → User Timesheet Position `on_update`
- sync_required: `no`
- run_targets:
  - `dinext_projects.tests.scenarios.iss_2026_03288_utp_act_dates.test_utp_act_dates`
- actors:
  - setup_user: `Administrator`
  - business_user: `test.iss-2026-03288-u@example.com`
- runtime_inputs:
  - переход UTP `Редактирование ↔ Согласовано`; `get_doc_before_save` / `_doc_before_save` обязателен для enter/leave
  - в факт идут только строки `User Timesheet Position Details` с `hours > 0`
  - `act_*` expand-only: не сужается и не очищается, если согласованных UTP не осталось
  - helper `change_position_status` зовёт `rollup_ut_status_and_task_dates` напрямую (эквивалент старого `execute_doc` SS), не полный UTP.save — чтобы не мешали workflow/utilization hooks
- reset_scope:
  - prefix `TEST ISS-2026-03288-U`
  - user `test.iss-2026-03288-u@example.com`
  - timesheet period `2026-04-07 .. 2026-04-13`
- primary_test_artifacts:
  - `test_utp_act_dates.py`
- last_run: 2026-08-12 — `dev.dinext.localhost`, `dinext-frappe-local-backend-1`, модуль `test_utp_act_dates` **9/9 OK**

## Status Legend

- ⚪ не составлен
- 🟡 не запущен
- 🟢 пройден
- 🔴 не пройден

## Test Cases

- 🟢 TC-01: Базовое согласование UTP по открытой задаче не меняет плановые даты, если факт внутри плана
  - surface: `Python`
  - setup: обычная Task Open, пустые `act_*`, `exp_*` заполнены, UTP с часами внутри окна
  - action: UTP → `Согласовано`
  - assert: `act_*` = min/max часов; `exp_*` без изменений
  - artifacts: `test_approved_utp_within_plan_keeps_expected_dates_unchanged`

- 🟢 TC-02: Возврат UTP из `Согласовано` в `Редактирование` не очищает `act_*`
  - surface: `Python`
  - action: согласовать, затем вернуть в `Редактирование`
  - assert: `act_*` остаются; статус Task не меняется
  - artifacts: `test_return_from_approved_to_editing_keeps_existing_fact`

- 🟢 TC-03: Повторное согласование той же UTP восстанавливает тот же фактический период
  - surface: `Python`
  - artifacts: `test_reapproving_same_position_restores_same_fact_range`

- 🟢 TC-04: Факт раньше планового старта сдвигает только `exp_start_date`
  - surface: `Python`
  - notes: `exp_*` пишет слой 2 на `Task.save()` из rollup
  - artifacts: `test_early_fact_moves_only_expected_start_date`

- 🟢 TC-05: Факт позже планового завершения сдвигает только `exp_end_date`
  - surface: `Python`
  - artifacts: `test_late_fact_moves_only_expected_end_date`

- 🟢 TC-08: Две согласованные UTP дают min/max по часам
  - surface: `Python`
  - artifacts: `test_two_approved_positions_aggregate_min_and_max_fact_dates`

- 🟢 TC-09: Повторный пересчёт не сужает и не очищает уже записанный факт
  - surface: `Python`
  - artifacts: `test_recalculation_does_not_shrink_or_clear_existing_fact`

- 🟢 TC-10: После вывода всех согласованных UTP факт на Task не очищается
  - surface: `Python`
  - artifacts: `test_removing_last_approved_position_after_series_keeps_fact`

- 🟢 TC-24: Оставшийся период не сужает текущий факт — `act_*` остаются широкими
  - surface: `Python`
  - artifacts: `test_non_shrinking_remaining_period_keeps_full_fact_range`

## Last run

- date: `2026-08-12`
- site: `dev.dinext.localhost`
- command: `docker exec dinext-frappe-local-backend-1 bench --site dev.dinext.localhost run-tests --module dinext_projects.tests.scenarios.iss_2026_03288_utp_act_dates.test_utp_act_dates`
- result: **9/9 OK**
- notes: adapter `ensure_task` — `Task.type` default `" "` (пробел) валит Link; ставим `Stage`. D2 не чиним.
