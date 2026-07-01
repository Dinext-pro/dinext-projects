# Work Efforts: baseline Server Script перед миграцией в Python

- scenario: `we_ss_migration_baseline`
- site: `dev.dinext.localhost` (или текущий `--site` bench)
- owner_app: `dinext_projects`
- dependent_apps:
  - `erpnext` (Project, Task, Fiscal Year)
  - `project_workload_assignment` (Project Workload Assignment — косвенная зависимость UI/forecast; не мутируется в сценарии)
- primary_surface: `Server Script`
- secondary_surfaces:
  - `Python` (целевое приложение после миграции — отдельный этап, не входит в этот baseline)
- scenario_dir: `frappe-bench/apps/dinext_projects/dinext_projects/dinext_projects/tests/scenarios/we_ss_migration_baseline/`
- data_helper: `data_setup.py`
- source_of_truth (Server Script, sandbox):
  - `.sandbox/demodev/server-script/api/Get Work Efforts Consolidated Data.py` → `get_work_efforts_consolidated_data`
  - `.sandbox/demodev/server-script/api/Calculate Timesheet Limits_V4.py` → `calculate_timesheet_limits`
  - `.sandbox/demodev/server-script/api/Save_Forecast_As_Plan.py` → `save_forecast_as_plan`
- sync_required: `no` (тесты вызывают активные Server Script на сайте; sandbox — справочник до миграции)
- run_targets:
  - `dinext_projects.dinext_projects.tests.scenarios.we_ss_migration_baseline.test_we_ss_baseline`
- Команда прогона (backend-контейнер):
  ```bash
  docker exec dinext-frappe-local-backend-1 bench --site dev.dinext.localhost run-tests --app dinext_projects --module dinext_projects.dinext_projects.tests.scenarios.we_ss_migration_baseline.test_we_ss_baseline
  ```
- actors:
  - setup_user: `Administrator`
  - business_user: `Administrator`
- runtime_inputs:
  - **Dependency (read-only):** проект `TEST-V15.106.0 (HEAD)` (~18 PWE) — не owned; golden TC-01/TC-02 привязаны к текущим данным сайта.
  - **Owned (mutation):** префикс `WE-SS-MIG-BASE` — Project/Task/PWE для TC-03.
  - `view_options`: `Прогноз и факт` (TC-01).
  - `positions` JSON + `timesheet_name` (TC-02).
  - `project` + `data` JSON array (TC-03).
- reset_scope:
  - owned: `Project`, `Task`, `Project Work Efforts`, `Project Role` с префиксом `WE-SS-MIG-BASE`
  - dependency `TEST-V15.106.0 (HEAD)` **не** изменяется и **не** удаляется

## Status Legend

- ⚪ не составлен runnable-артефакт
- 🟡 runnable есть, успешный прогон не зафиксирован
- 🟢 последний прогон успешен
- 🔴 последний прогон с падением

## Test Cases

- 🟢 TC-01: `get_work_efforts_consolidated_data` — нормализованный ответ vs `fixtures/tc01_consolidated_golden.json`
  - surface: `Server Script` | actor: `business_user`
  - dependency: `TEST-V15.106.0 (HEAD)` (read-only)
  - artifacts: `test_tc01_*`, `fixtures/tc01_consolidated_golden.json`
  - normalize: sort tasks/roles; round plan/forecast/fact floats; strip `fact_utps_*`

- 🟢 TC-02: `calculate_timesheet_limits` — positions payload из golden vs `fixtures/tc02_limits_golden.json`
  - surface: `Server Script` | actor: `business_user`
  - dependency: UTP на `TEST-V15.106.0 (HEAD)` (захвачен в golden `positions_payload`)
  - artifacts: `test_tc02_*`, `fixtures/tc02_limits_golden.json`

- 🟢 TC-03: `save_forecast_as_plan` — owned PWE, plan меняется на forecast value
  - surface: `Server Script` | actor: `business_user`
  - owned: `WE-SS-MIG-BASE` Project/Task/PWE
  - artifacts: `test_tc03_*`, `prepare_case_save_forecast_as_plan`
  - assert: `pwea_plan` после вызова = `TC03_FORECAST_PLAN` (48.5)

## Primary test artifacts

- `test_we_ss_baseline.py` — TC-01 … TC-03
- `data_setup.py` — PREFIX, dependency constants, owned prepare/reset
- `fixtures/tc01_consolidated_golden.json` — эталон TC-01 (**capture**)
- `fixtures/tc02_limits_golden.json` — эталон TC-02 (**capture**)
- `.sandbox/local/scripts/capture_golden.py` — helper захвата golden через `bench execute`

## Capture golden

Из корня workspace (нужен запущенный `dinext-frappe-local-backend-1`):

```bash
python .sandbox/local/scripts/capture_golden.py
```

Или напрямую:

```bash
docker exec dinext-frappe-local-backend-1 bench --site dev.dinext.localhost execute dinext_projects.dinext_projects.tests.scenarios.we_ss_migration_baseline.capture_fixtures.run
```

Переснимать golden после **намеренного** изменения Server Script или dependency-данных `TEST-V15.106.0 (HEAD)`.

## Side effects

- TC-03 создаёт и изменяет owned PWE; `tearDown` удаляет документы с префиксом `WE-SS-MIG-BASE`.
- TC-01/TC-02 read-only для dependency project.
