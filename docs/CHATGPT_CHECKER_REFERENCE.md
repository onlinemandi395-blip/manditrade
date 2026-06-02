# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-02 after the performance + scalability + state-management hardening pass.

## Final Role Model

- Active roles:
  - `platform_admin`
  - `manufacturer`
  - `mahajan`
  - `public_buyer`
  - `worker`
- Removed from live RBAC:
  - `client`

## Final Commerce Model

- `Marketplace`
  - public-buyer shopping lane
  - seller payout goes directly to manufacturer
- `MandiPlace`
  - manufacturer procurement and B2B lane
  - admin-routed supply workflow
- `Raw Materials`
  - admin + mahajan supply-management lane
  - manufacturers participate through admin-routed supply requests
- `Suta Mandi`
  - manufacturer-only yarn / suta buying surface
  - fulfilled through admin + mahajan routing

## Operations Center Status

- Admin now has a dedicated `Operations Center` route and page:
  - [modules/admin/operations_dashboard.py](/c:/2026/manditrade/manditrade/modules/admin/operations_dashboard.py)
- Navigation and route access are wired through:
  - [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py)
  - [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py)
- Current operational sections include:
  - commerce health
  - supply health
  - financial health
  - workforce health
  - platform health
  - alerts
  - recommendations
  - operational search
  - automation task runner

## State Management Status

- Centralized runtime UI state now exists in:
  - [services/session_state_service.py](/c:/2026/manditrade/manditrade/services/session_state_service.py)
- Active usage is now wired into shared navigation and page helpers:
  - [bootstrap/app_bootstrap.py](/c:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [utils/page_ui.py](/c:/2026/manditrade/manditrade/utils/page_ui.py)
  - [utils/deep_links.py](/c:/2026/manditrade/manditrade/utils/deep_links.py)
- Centralized state currently covers:
  - active role / context
  - active order selection
  - page filters
  - active tabs
  - sidebar navigation memory
  - deep links
  - operational search state

## Cache Layer Status

- Lightweight in-memory TTL caching now exists in:
  - [services/cache_service.py](/c:/2026/manditrade/manditrade/services/cache_service.py)
- Current cache support includes:
  - JSON read caching
  - generic computed-result caching
  - TTL-based invalidation
  - manual namespace/key invalidation
  - role-safe cache key support
- Safe writes now invalidate cached JSON reads through:
  - [services/safe_drive_write_service.py](/c:/2026/manditrade/manditrade/services/safe_drive_write_service.py)

## Query Engine Status

- Shared filtering / sorting / pagination query layer now exists in:
  - [services/query_engine.py](/c:/2026/manditrade/manditrade/services/query_engine.py)
- Current standardized query support includes:
  - search filtering
  - status filtering
  - date-range filtering
  - numeric price filtering
  - sort selection
  - page slicing

## Pagination Status

- Reusable pagination table component now exists in:
  - [components/paginated_table.py](/c:/2026/manditrade/manditrade/components/paginated_table.py)
- Current operational usage includes:
  - [modules/admin/operations_dashboard.py](/c:/2026/manditrade/manditrade/modules/admin/operations_dashboard.py)
  - [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)
  - [modules/notifications/dashboard.py](/c:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- Pagination currently preserves:
  - page state
  - filter state
  - next / previous navigation
  - standardized record counts

## Alert Engine Status

- Reusable alert engine now exists in:
  - [services/alert_engine.py](/c:/2026/manditrade/manditrade/services/alert_engine.py)
- Alerts persist centrally in runtime storage and currently cover:
  - overdue payments
  - stalled mandi orders
  - delayed dispatches
  - low raw-material stock
  - unverified public payments
  - inactive manufacturers
  - inactive mahajans
  - failed logistics updates
  - pending approvals too long

## Recommendation Engine Status

- Rule-based recommendation service now exists in:
  - [services/recommendation_service.py](/c:/2026/manditrade/manditrade/services/recommendation_service.py)
- Recommendations now generate for:
  - `platform_admin`
  - `manufacturer`
  - `mahajan`

## KPI Engine Status

- Reusable KPI calculator now exists in:
  - [services/kpi_service.py](/c:/2026/manditrade/manditrade/services/kpi_service.py)
- Current KPI coverage includes:
  - marketplace orders / revenue
  - active mandi orders
  - fulfillment and supplier response timing
  - dispatch and low-stock rates
  - outstanding ledger and commission pending
  - jobs filled and worker response rate
  - manufacturer / mahajan / platform health scores

## Automation Task Status

- Scheduler-compatible automation utilities now exist in:
  - [services/automation_tasks.py](/c:/2026/manditrade/manditrade/services/automation_tasks.py)
- Current task entry points:
  - `run_hourly_tasks()`
  - `run_daily_tasks()`
- Current automated actions:
  - recompute KPI snapshot
  - generate alerts
  - refresh recommendations
  - archive old audit logs
  - write hourly / daily task summaries
  - write hourly / daily analytics snapshots

## Snapshot Status

- Historical operational snapshots now persist under:
  - `app_runtime/analytics_snapshots/`
- Current snapshots include prepared daily / hourly payloads for:
  - KPI summaries
  - alert snapshot totals
  - recommendation summaries
- KPI and recommendation UIs now prefer reading prepared outputs before recomputing:
  - [modules/admin/operations_dashboard.py](/c:/2026/manditrade/manditrade/modules/admin/operations_dashboard.py)
  - [modules/analytics/dashboard.py](/c:/2026/manditrade/manditrade/modules/analytics/dashboard.py)

## Operational Search Status

- Global admin operational search now exists in:
  - [services/operational_search_service.py](/c:/2026/manditrade/manditrade/services/operational_search_service.py)
- Search currently covers:
  - manufacturers
  - mahajans
  - products
  - raw materials
  - mandi / supply orders
  - marketplace orders
  - ledger entries
- Prepared search indexing now persists to:
  - `app_runtime/search_index/latest.json`
- Admin recovery tools can rebuild the operational search index from:
  - [modules/system/health_dashboard.py](/c:/2026/manditrade/manditrade/modules/system/health_dashboard.py)

## Event Bus Status

- Lightweight local event hooks now exist in:
  - [services/event_bus.py](/c:/2026/manditrade/manditrade/services/event_bus.py)
- Runtime availability is wired through:
  - [bootstrap/service_container.py](/c:/2026/manditrade/manditrade/bootstrap/service_container.py)
- Current published lifecycle events include:
  - `HOURLY_TASKS_COMPLETED`
  - `DAILY_TASKS_COMPLETED`

## Safe Write Status

- Atomic write helper now exists in:
  - [utils/file_locking.py](/c:/2026/manditrade/manditrade/utils/file_locking.py)
- JSON persistence now routes through atomic replacement in:
  - [services/json_service.py](/c:/2026/manditrade/manditrade/services/json_service.py)
- Safe document mutation remains centralized in:
  - [services/safe_drive_write_service.py](/c:/2026/manditrade/manditrade/services/safe_drive_write_service.py)
- Recovery actions now support:
  - rebuild search index
  - refresh KPI snapshot
  - regenerate alerts
  - repair snapshots

## Audit Intelligence Status

- Structured governance logs remain in:
  - `app_runtime/audit/audit_logs/`
- Audit filtering and summaries now support:
  - actor filter
  - entity filter
  - severity filter
  - summary counts
  - old-log archival
- Main implementation:
  - [services/audit_service.py](/c:/2026/manditrade/manditrade/services/audit_service.py)

## Analytics Maturity Status

- Analytics now reads from the KPI engine and shows stronger operational summaries in:
  - [modules/analytics/dashboard.py](/c:/2026/manditrade/manditrade/modules/analytics/dashboard.py)
- Current admin analytics now include:
  - KPI summary cards
  - public marketplace trends
  - raw-material trend charts
  - finance snapshots

## Jobs Lifecycle Status

- Jobs lifecycle is now more mature in:
  - [services/job_service.py](/c:/2026/manditrade/manditrade/services/job_service.py)
  - [modules/jobs/dashboard.py](/c:/2026/manditrade/manditrade/modules/jobs/dashboard.py)
- Current job lifecycle support includes:
  - `ACTIVE`
  - `PAUSED`
  - `CLOSED`
  - `ARCHIVED`
- Additional worker-selection state now includes:
  - shortlist tracking
  - selected application tracking

## Status / Workflow Support

- Reusable filtering and search helpers:
  - [utils/filtering.py](/c:/2026/manditrade/manditrade/utils/filtering.py)
  - [components/filter_bar.py](/c:/2026/manditrade/manditrade/components/filter_bar.py)
- Reusable timeline rendering:
  - [components/timeline.py](/c:/2026/manditrade/manditrade/components/timeline.py)
  - [components/order_timeline.py](/c:/2026/manditrade/manditrade/components/order_timeline.py)
- Centralized status styling:
  - [utils/status_styles.py](/c:/2026/manditrade/manditrade/utils/status_styles.py)
- Export utilities:
  - [utils/export_utils.py](/c:/2026/manditrade/manditrade/utils/export_utils.py)
- Deep-link helpers:
  - [utils/deep_links.py](/c:/2026/manditrade/manditrade/utils/deep_links.py)

## Compatibility Note

- Internal compatibility fields such as `client_price`, `suggested_client_price`, and `approved_client_price` still remain in selected storage/service paths where current data flow depends on them.
- These compatibility fields are not part of live RBAC or live user-facing terminology.

## Stress-Test Status

- Dedicated hardening coverage now exists in:
  - [tests/test_scalability_hardening.py](/c:/2026/manditrade/manditrade/tests/test_scalability_hardening.py)
- Current simulation coverage includes:
  - large query-set filtering over `5000` synthetic rows
  - cache invalidation behavior
  - indexed search rebuild
  - automation snapshot persistence
  - event publication
  - pagination rendering

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `193`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

## Remaining Blockers

- Alerts and recommendations are intentionally rule-based and deterministic; there is still no forecasting depth or adaptive scoring beyond current heuristics.
- Pagination is implemented on the current highest-volume operational pages, but a few legacy / low-traffic screens still use direct table rendering and can be migrated later.
- Operational search currently routes to page-level detail surfaces, not a universal modal detail shell.
- Legacy compatibility-only internal names from the old client-era data model still exist and should only be removed in a dedicated migration pass.
