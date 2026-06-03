# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-03 after the admin-routed manufacturer MandiPlace procurement and packaging/courier services pass.

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
  - admin-routed co-manufacturer workflow
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
  - MandiPlace procurement volume snapshot

## Admin-Routed Manufacturer Procurement Status

- Manufacturer-to-manufacturer MandiPlace procurement is now admin-routed through:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)
- Current flow support includes:
  - manufacturer request creation
  - admin co-manufacturer assignment
  - supplier quote submission
  - admin downstream price setting
  - packaging selection
  - courier booking
  - requester confirmation
  - supplier dispatch
  - delivered / received / closed progression
- Direct manufacturer-to-manufacturer bypass remains blocked in the live workflow.

## Co-Manufacturer Assignment Status

- Supplier eligibility is currently enforced with:
  - active manufacturer status
  - product availability for MandiPlace
  - supplier-owned mandi-visible inventory
  - requester and supplier must be different manufacturers
- Main implementation:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [services/dual_inventory_service.py](/c:/2026/manditrade/manditrade/services/dual_inventory_service.py)

## Packaging Service Status

- Admin packaging catalog now exists in:
  - [modules/admin/packaging_services.py](/c:/2026/manditrade/manditrade/modules/admin/packaging_services.py)
  - [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
- Current support includes:
  - create
  - update pricing
  - archive
  - apply packaging to MandiPlace order

## Courier Service Status

- Admin courier catalog now exists in:
  - [modules/admin/courier_services.py](/c:/2026/manditrade/manditrade/modules/admin/courier_services.py)
  - [modules/logistics/dashboard.py](/c:/2026/manditrade/manditrade/modules/logistics/dashboard.py)
  - [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
- Current support includes:
  - create
  - update rate card
  - archive
  - book courier on MandiPlace order
  - track courier delivery state

## Final Cost Calculation Status

- MandiPlace cost breakdown now calculates:
  - goods amount
  - supplier amount
  - spread
  - admin commission
  - packaging cost
  - courier cost
  - final payable
- Main pricing implementation:
  - [services/pricing_service.py](/c:/2026/manditrade/manditrade/services/pricing_service.py)

## Commission / Ledger Status

- MandiPlace confirmation now creates:
  - manufacturer-to-supplier goods ledger
  - manufacturer-to-admin commission ledger
  - manufacturer-to-admin service ledger when packaging/courier charges exist
- Main implementation:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [services/ledger_service.py](/c:/2026/manditrade/manditrade/services/ledger_service.py)

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

## Drive JSON Folder Model Status

- Canonical Drive-oriented path design now exists in:
  - [services/drive_path_service.py](/c:/2026/manditrade/manditrade/services/drive_path_service.py)
- Current centralized path coverage includes:
  - registry paths
  - catalog paths
  - monthly order partitions
  - notification queue/history/dead-letter paths
  - audit paths
  - media folders
- The hardening pass is compatibility-safe:
  - path centralization is live in code
  - full physical live-data cutover is still deferred until migration is executed and validated

## Storage Migration Status

- Storage migration orchestration now exists in:
  - [services/storage_migration_service.py](/c:/2026/manditrade/manditrade/services/storage_migration_service.py)
- Current migration support includes:
  - legacy path discovery
  - dry-run and execute modes
  - rehearsal execute mode
  - canonical-path writes through safe write service
  - duplicate-safe merge behavior
  - entity normalization
  - mode-specific migration report generation
- Main operator script:
  - [scripts/migrate_storage_to_canonical.py](/c:/2026/manditrade/manditrade/scripts/migrate_storage_to_canonical.py)
- Rehearsal operator script:
  - [scripts/run_storage_migration_rehearsal.py](/c:/2026/manditrade/manditrade/scripts/run_storage_migration_rehearsal.py)

## Canonical Validation Status

- Canonical storage validation now exists in:
  - [services/canonical_storage_validation_service.py](/c:/2026/manditrade/manditrade/services/canonical_storage_validation_service.py)
  - [scripts/validate_canonical_storage.py](/c:/2026/manditrade/manditrade/scripts/validate_canonical_storage.py)
- Validation currently checks:
  - canonical folder presence
  - required JSON readability
  - legacy-vs-canonical gap warnings
  - queue/media/schema readiness at a lightweight level
  - persisted validation report status for cutover review

## Storage Mode Status

- Storage mode toggle is now present in:
  - [configs/system_config.json](/c:/2026/manditrade/manditrade/configs/system_config.json)
- Current mode fields:
  - `storage.mode`
  - `storage.allow_legacy_fallback`
- Default remains:
  - `compatibility`
- Canonical mode switching is now path-layer aware in:
  - [services/drive_path_service.py](/c:/2026/manditrade/manditrade/services/drive_path_service.py)
- Canonical mode is now startup-guarded through:
  - [services/storage_cutover_service.py](/c:/2026/manditrade/manditrade/services/storage_cutover_service.py)
  - [bootstrap/service_container.py](/c:/2026/manditrade/manditrade/bootstrap/service_container.py)
  - [bootstrap/app_bootstrap.py](/c:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
- Unsafe canonical startup now blocks with:
  - `Canonical storage mode requested, but validated migration report is missing.`

## Cutover Readiness Status

- Shared cutover readiness evaluation now exists in:
  - [services/storage_cutover_service.py](/c:/2026/manditrade/manditrade/services/storage_cutover_service.py)
- Readiness report generator now exists in:
  - [scripts/generate_cutover_readiness_report.py](/c:/2026/manditrade/manditrade/scripts/generate_cutover_readiness_report.py)
- Current readiness requirements are:
  - last execute migration recommendation = `PASS`
  - canonical validation status = `PASS`
  - critical validation errors = `0`
  - record and checksum checks must remain acceptable

## System Health Migration Status

- Admin migration panel is now available in:
  - [modules/system/health_dashboard.py](/c:/2026/manditrade/manditrade/modules/system/health_dashboard.py)
- Current panel shows:
  - current storage mode
  - last dry-run status
  - last execute status
  - last validation status
  - canonical readiness
  - blocking issues
  - recommended next action
  - latest migration report
  - canonical validation result
  - dry-run trigger
  - validation trigger
  - cutover readiness report trigger

## Path Service Status

- Existing manufacturer workspace path logic remains in:
  - [services/domain_paths_service.py](/c:/2026/manditrade/manditrade/services/domain_paths_service.py)
- It now cooperates with the centralized Drive path layer for:
  - registry lookups
  - catalog lookups
  - notification-channel paths

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

## Event Notification Status

- Central event-to-notification orchestration now exists in:
  - [services/event_notification_service.py](/c:/2026/manditrade/manditrade/services/event_notification_service.py)
- Current routed event coverage includes:
  - product approval request / approval / rejection
  - raw material create / update
  - marketplace order create
  - payment submitted / verified
  - supply order created / assigned / confirmed
  - logistics updates
  - job create / application updates
  - archive events

## Gmail Queue Status

- Gmail notifications now queue first through:
  - [services/gmail_service.py](/c:/2026/manditrade/manditrade/services/gmail_service.py)
- Current flow is:
  - event emitted
  - in-app notification written if routed
  - email queued
  - queue processor writes history on send simulation/live send
  - repeated failures land in dead letter
- Current queue storage coverage includes:
  - queue
  - history
  - retry state
  - failed dead-letter handling

## In-App Notification Routing Status

- In-app notification entities now carry richer routing fields including:
  - `source_route`
  - `deep_link`
  - `recipient_role`
  - `severity`
- Main implementation remains in:
  - [services/notification_center_service.py](/c:/2026/manditrade/manditrade/services/notification_center_service.py)
  - [modules/notifications/dashboard.py](/c:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- Platform admin notification console now exposes:
  - In-App
  - Email Queue
  - Email History
  - Dead Letter
  - Rules

## CRUD Hook Coverage Status

- Event hooks are now explicitly wired into major domains:
  - [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
  - [services/product_catalog_service.py](/c:/2026/manditrade/manditrade/services/product_catalog_service.py)
  - [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py)
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [services/job_service.py](/c:/2026/manditrade/manditrade/services/job_service.py)
- Notification failure is now isolated from core business commit:
  - queue and dead-letter failures do not roll back the underlying business write

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

## Release Packaging Status

- Release packaging docs now exist at:
  - [PILOT_RELEASE_CHECKLIST.md](/c:/2026/manditrade/manditrade/PILOT_RELEASE_CHECKLIST.md)
  - [PILOT_OPERATOR_GUIDE.md](/c:/2026/manditrade/manditrade/PILOT_OPERATOR_GUIDE.md)
  - [DEPLOYMENT.md](/c:/2026/manditrade/manditrade/DEPLOYMENT.md)
- Release utility scripts now exist at:
  - [scripts/validate_release_env.py](/c:/2026/manditrade/manditrade/scripts/validate_release_env.py)
  - [scripts/cleanup_test_data.py](/c:/2026/manditrade/manditrade/scripts/cleanup_test_data.py)
  - [scripts/create_release_snapshot.py](/c:/2026/manditrade/manditrade/scripts/create_release_snapshot.py)

## Product Images Status

- Shared image handling now exists in:
  - [services/image_service.py](/c:/2026/manditrade/manditrade/services/image_service.py)
- Products now support normalized image metadata:
  - `image_url`
  - `image_file_ref`
  - `thumbnail_url`
  - `image_alt_text`
  - `image_status`
- Product image support is wired through:
  - [services/product_catalog_service.py](/c:/2026/manditrade/manditrade/services/product_catalog_service.py)
  - [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)
- Missing or broken images now fall back to a deterministic placeholder image instead of a dead image surface.

## Raw Material Images Status

- Raw material image metadata is now stored in:
  - [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
- Raw material image inputs are now available in:
  - [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py)
  - [modules/suta_mandi/dashboard.py](/c:/2026/manditrade/manditrade/modules/suta_mandi/dashboard.py)
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)

## Cart UX Status

- Shared cart logic now exists in:
  - [services/cart_service.py](/c:/2026/manditrade/manditrade/services/cart_service.py)
- Compatibility wrapper for public buyers remains in:
  - [services/public_cart_service.py](/c:/2026/manditrade/manditrade/services/public_cart_service.py)
- Current checkout routing is:
  - `MARKETPLACE`
    - public buyer -> marketplace order
  - `MANDIPLACE`
    - manufacturer -> admin-routed mandi supply request
  - `SUTA_MANDI`
    - manufacturer -> admin-routed suta supply request
- Direct manufacturer-to-mahajan bypass is still blocked.

## Thumbnail Shopping Status

- Shared thumbnail card component now exists in:
  - [components/product_card.py](/c:/2026/manditrade/manditrade/components/product_card.py)
- Card-based shopping or request surfaces now appear in:
  - [modules/marketplace/dashboard.py](/c:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)
  - [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)
  - [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py)
  - [modules/suta_mandi/dashboard.py](/c:/2026/manditrade/manditrade/modules/suta_mandi/dashboard.py)
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)
- Marketplace detail selection now shows:
  - larger image area
  - description
  - role-safe price
  - quantity selector
  - add-to-cart action
- Public buyer pricing remains restricted to marketplace pricing only.

## Order Detail UX Status

- Shared order detail renderer now exists in:
  - [components/order_detail_view.py](/c:/2026/manditrade/manditrade/components/order_detail_view.py)
- Rich detail rendering is now wired into:
  - [modules/public_orders/dashboard.py](/c:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)
- Current detail view coverage includes:
  - order ID
  - items with thumbnails
  - quantity and subtotal visibility
  - logistics snapshot
  - payment snapshot
  - notes
  - timeline with actor and timestamp context

## Payment Proof Status

- Marketplace orders now persist:
  - `payment_proof_url`
  - `payment_proof_uploaded_at`
  - `payment_verified_by`
  - `payment_verified_at`
- Supply / mandi orders now persist the same metadata in:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
- Public order proof submission and verification remain in:
  - [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py)

## Favorites Status

- Lightweight favorites support now exists in:
  - [services/favorites_service.py](/c:/2026/manditrade/manditrade/services/favorites_service.py)
- Public marketplace buyers can now save products from:
  - [modules/marketplace/dashboard.py](/c:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)

## Ratings Status

- Marketplace product feedback now persists on public orders in:
  - [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py)
- Supply-experience ratings now persist on mandi / supply orders in:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)

## Trust Badge Status

- Rule-based trust badge calculation now exists in:
  - [services/trust_badge_service.py](/c:/2026/manditrade/manditrade/services/trust_badge_service.py)
- Current trust signals include:
  - payment verified
  - fast dispatch
  - top rated product
  - reliable mahajan
  - trusted supply partner

## Reorder Status

- Repeat-order prefilling now works through the shared cart layer:
  - [services/cart_service.py](/c:/2026/manditrade/manditrade/services/cart_service.py)
  - [services/public_cart_service.py](/c:/2026/manditrade/manditrade/services/public_cart_service.py)
- Public buyer order history now supports repeat-cart behavior from:
  - [modules/public_orders/dashboard.py](/c:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)

## Notification UX Status

- Notifications now support richer metadata fields:
  - `source_route`
  - `thumbnail_url`
  - `severity`
  - `recipient_role`
  - `deep_link`
- Main implementation remains in:
  - [services/notification_center_service.py](/c:/2026/manditrade/manditrade/services/notification_center_service.py)
  - [modules/notifications/dashboard.py](/c:/2026/manditrade/manditrade/modules/notifications/dashboard.py)

## Environment Validation Status

- Release env validation script now runs and writes reports to:
  - `runtime/release_reports/`
- Latest validation result:
  - `FAIL`
- Current release blockers from the latest script run:
  - staging cloud runtime is still using a localhost OAuth redirect URI
  - admin sender email still uses a `.local` placeholder
- Latest report file:
  - `runtime/release_reports/latest_release_env.json`

## Cleanup Script Status

- Test-data cleanup script now supports:
  - `python scripts/cleanup_test_data.py --dry-run`
  - `python scripts/cleanup_test_data.py --execute`
- Current dry-run result against seeded runtime data:
  - `8` files would be rewritten
  - `23` files would be archived
  - `20` tagged demo/test records would be removed
- Cleanup archive target:
  - `runtime/release_cleanup/`

## Release Snapshot Status

- Release snapshot script now writes to:
  - `runtime/release_snapshots/`
- Latest snapshot result:
  - recommendation: `NO_GO`
- Current snapshot is blocking release because:
  - latest environment validation is failing
- Latest snapshot file:
  - `runtime/release_snapshots/release_snapshot_20260602_154730.json`

## Operator Guide Status

- Pilot operator guide now exists in:
  - [PILOT_OPERATOR_GUIDE.md](/c:/2026/manditrade/manditrade/PILOT_OPERATOR_GUIDE.md)
- Current coverage includes:
  - daily checks
  - incident handling
  - severity model
  - storage migration rehearsal
  - rollback to compatibility mode
  - release gate command sequence

## Smoke Test Status

- Release smoke coverage now exists in:
  - [tests/test_release_smoke.py](/c:/2026/manditrade/manditrade/tests/test_release_smoke.py)
- Current smoke coverage verifies:
  - all nav routes dispatch for each live role
  - unauthorized routes stay blocked
  - pre-login nav is `Dashboard` only
  - sidebar login surface exists
  - duplicate login copy is not present

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
  - Passed: `239`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

## GO / NO-GO

- Current recommendation: `NO_GO`
- Reason:
  - app behavior, smoke tests, compile, and import are clean
  - pilot release environment is still blocked by cloud OAuth redirect and admin sender email configuration
- Release can move to `GO` after:
  - non-localhost cloud redirect URI is configured
  - real admin sender email replaces the `.local` placeholder
  - `python scripts/validate_release_env.py` returns `PASS`

## Remaining Blockers

- Release readiness is still blocked by cloud OAuth/admin email configuration, so this is not yet a pilot `GO`.
- Card-based shopping is now live on the main marketplace and manufacturer request surfaces, but some lower-traffic admin/supervisory tables still remain table-first rather than card-first by design.
- Favorites are currently wired into the marketplace flow first; manufacturer-side saved-item UX can be expanded further on additional shopping surfaces later.
- Canonical pathing, rehearsal tooling, validation, and cutover guards are now in place, but production cutover still depends on an operator-reviewed execute run plus explicit `storage.mode=canonical` switch after readiness says `READY`.
- MandiPlace manufacturer procurement is now routed through admin with packaging and courier support, but packaging/courier charges are still modeled for admin-led settlement rather than a fuller configurable recipient matrix.
- Alerts and recommendations are intentionally rule-based and deterministic; there is still no forecasting depth or adaptive scoring beyond current heuristics.
- Pagination is implemented on the current highest-volume operational pages, but a few legacy / low-traffic screens still use direct table rendering and can be migrated later.
- Operational search currently routes to page-level detail surfaces, not a universal modal detail shell.
- Legacy compatibility-only internal names from the old client-era data model still exist and should only be removed in a dedicated migration pass.
