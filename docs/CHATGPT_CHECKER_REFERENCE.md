# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-01 after the operational sidebar-page pass.

## All Navigation Pages Operational Status

- Central navigation remains defined in [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py).
- Sidebar routes remain centralized in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- Every label currently present in `ROLE_NAVIGATION_MAP` now routes to a non-blank screen.
- Pages that were previously summary-only or placeholder-light now expose at least:
  - page hero/header
  - metric section
  - horizontal tabs
  - role-safe empty state or action surface

## Tabbed Page Status

Tabbed layouts are now present across the main navigation surfaces, including:

- [modules/actions/dashboard.py](/c:/2026/manditrade/manditrade/modules/actions/dashboard.py)
- [modules/notifications/dashboard.py](/c:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- [modules/profile/dashboard.py](/c:/2026/manditrade/manditrade/modules/profile/dashboard.py)
- [modules/manufacturer/dashboard.py](/c:/2026/manditrade/manditrade/modules/manufacturer/dashboard.py)
- [modules/client/dashboard.py](/c:/2026/manditrade/manditrade/modules/client/dashboard.py)
- [modules/mahajan/dashboard.py](/c:/2026/manditrade/manditrade/modules/mahajan/dashboard.py)
- [modules/payments/dashboard.py](/c:/2026/manditrade/manditrade/modules/payments/dashboard.py)
- [modules/ledger/dashboard.py](/c:/2026/manditrade/manditrade/modules/ledger/dashboard.py)
- [modules/public_orders/dashboard.py](/c:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)
- [modules/analytics/dashboard.py](/c:/2026/manditrade/manditrade/modules/analytics/dashboard.py)

Existing tabs already present in product, inventory, client registry, jobs, system health, and product approvals were preserved.

## Clickable Count Dashboard Status

- Shared helper added in [utils/page_ui.py](/c:/2026/manditrade/manditrade/utils/page_ui.py).
- Helper functions now include:
  - `render_metric_card_button`
  - `render_metric_button_row`
  - `set_active_tab_from_metric`
  - `render_empty_state`
  - `render_status_chip`
- Clickable metric rows now exist on the main operational pages listed above.
- Current behavior:
  - clicking a metric stores page tab/filter intent in `st.session_state`
  - relevant tabs and filtered table areas render on the target page
- This is a Streamlit-safe implementation rather than custom JS card navigation.

## CRUD / Action Coverage By Page

- `My Profile`
  - admin, manufacturer, client, worker, public buyer, and mahajan now all have role-specific profile surfaces
  - manufacturer/client/worker/public buyer keep editable forms
  - mahajan now has a dedicated profile surface instead of falling through to a generic fallback
- `Notifications`
  - mark read
  - mark resolved
  - remind tomorrow
  - public-buyer and manufacturer/admin notification status updates stay role-safe
- `My Actions`
  - grouped into pending/high-priority/due-today/completed tabs
  - action cards remain operational summary surfaces
- `Payments`
  - reminder trigger remains available for manufacturer-linked payment follow-up
  - other roles get role-safe summary tabs instead of blank action space
- `Ledger`
  - overview, entries, due/overdue, and payment tabs added
  - add-payment flow now available from the ledger page
- `Marketplace Orders`
  - public-buyer flow and seller/admin flow both now use overview/orders/payments/delivery tabs
  - payment-reference, verify, confirm, and dispatch actions remain intact
- `Mahajan` / `Raw Materials`
  - overview, catalog, add-raw-material, and activity tabs now exist
  - current raw-material create flow is lightweight and local to the page surface

## RBAC Enforcement Status

- Route guard remains centralized in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- Sidebar hiding is still not the only control layer.
- Effective-role sidebar behavior remains dynamic in [bootstrap/app_bootstrap.py](/c:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py).
- Key RBAC guarantees still hold:
  - `platform_admin` gets governance and aggregate-only private-business views
  - `manufacturer` sees own workspace only
  - `mahajan` remains limited to admin-supply pages
  - `client` sees own client-scope data only
  - `public_buyer` stays in public-marketplace scope only
  - `worker` stays in worker/job scope only

## Production UI Status

- Normal pages do not expose runtime debug text, OAuth config details, fallback flags, or mock-login controls.
- Diagnostics remain concentrated in [modules/system/health_dashboard.py](/c:/2026/manditrade/manditrade/modules/system/health_dashboard.py).
- Public pre-login navigation still shows `Dashboard` only, and marketplace remains hidden before login.

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `150`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

Additional operational-nav coverage now checks:

- all centralized nav items are represented in route registry source
- operational pages include tabs
- clickable metric helper wiring exists
- mahajan profile has a dedicated renderer

## Remaining Blockers

- `Mahajan` and `Raw Materials` are now operational tabbed pages, but they still use lightweight in-page actions rather than a fully persisted supplier catalog workflow.
- Clickable metric cards currently drive tab/filter intent through session state; they do not force true tab switching in the browser because Streamlit tabs are not fully programmatically controlled.
- Internal RFQ/procurement naming still exists in some services/modules for compatibility, even though user-facing routing remains normalized to `Mandi Orders`.
