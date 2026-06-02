# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-02 after the operations maturity + UX hardening pass.

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

## Operations Maturity Status

- Reusable filtering and search helpers now exist in:
  - [utils/filtering.py](/c:/2026/manditrade/manditrade/utils/filtering.py)
  - [components/filter_bar.py](/c:/2026/manditrade/manditrade/components/filter_bar.py)
- Reusable timeline rendering now exists in:
  - [components/timeline.py](/c:/2026/manditrade/manditrade/components/timeline.py)
  - [components/order_timeline.py](/c:/2026/manditrade/manditrade/components/order_timeline.py)
- Centralized status styling now exists in:
  - [utils/status_styles.py](/c:/2026/manditrade/manditrade/utils/status_styles.py)
- Export utilities now exist in:
  - [utils/export_utils.py](/c:/2026/manditrade/manditrade/utils/export_utils.py)
- Notification deep-link helpers now exist in:
  - [utils/deep_links.py](/c:/2026/manditrade/manditrade/utils/deep_links.py)

## Workflow Visibility Status

- `Mandi Orders` now supports:
  - KPI filter cards
  - reusable filter/search layer
  - export to CSV / JSON
  - role-aware order detail
  - logistics console visibility
  - admin logistics update controls
- Main implementation:
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)

- `Marketplace Orders` now supports:
  - reusable filter/search layer
  - visual timeline
  - logistics visibility
  - admin logistics updates
  - export to CSV / JSON
- Main implementation:
  - [modules/public_orders/dashboard.py](/c:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)

- `Notifications` now supports:
  - filter/search
  - export
  - related-record deep links
  - better empty states
- Main implementation:
  - [modules/notifications/dashboard.py](/c:/2026/manditrade/manditrade/modules/notifications/dashboard.py)

## Logistics Console Status

- Marketplace logistics are persisted in [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py).
- Mandi / supply logistics are persisted in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).
- Admin remains the logistics owner across marketplace and supply flows.

## Audit Logging Status

- Structured governance logs are now written under:
  - `app_runtime/audit/audit_logs/`
- Logging service:
  - [services/audit_service.py](/c:/2026/manditrade/manditrade/services/audit_service.py)
- Current audit coverage includes:
  - product upserts / archive
  - manufacturer upserts / archive
  - mahajan upserts / archive
  - raw-material upserts
  - supply-order lifecycle updates
  - supply-ledger creation
  - marketplace payment and logistics updates

## Archive Model Status

- Hard-delete behavior for live admin registry actions is replaced by archive status updates for:
  - products
  - manufacturers
  - mahajans
- Archive behavior is handled in:
  - [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
- Current lifecycle set in live UI now includes `ARCHIVED` where relevant.

## Search / Filter Status

- Reusable search/filter is now applied across major operational pages including:
  - `Marketplace Orders`
  - `Mandi Orders`
  - `Products`
  - `Raw Materials`
  - `Payments`
  - `Ledger`
  - `Jobs`
  - `Notifications`
  - `Manufacturers`
  - `Mahajans`
  - `Suta Mandi`

## Raw Material vs Product Separation Status

- Finished-product wording remains on:
  - [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)
- Supply-input wording remains on:
  - [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py)
  - [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)
  - [modules/suta_mandi/dashboard.py](/c:/2026/manditrade/manditrade/modules/suta_mandi/dashboard.py)

## Suta Mandi Status

- `Suta Mandi` remains manufacturer-only.
- Suta catalog filtering/export now exists.
- Public-buyer and mahajan public exposure remain blocked by route + navigation rules.

## Compatibility Note

- Internal compatibility fields such as `client_price`, `suggested_client_price`, and `approved_client_price` still remain in selected storage/service paths where current data flow depends on them.
- These compatibility fields are not part of live RBAC or live user-facing terminology.

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `177`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

## Remaining Blockers

- Some pages still use simple `st.dataframe(...)` detail surfaces after filtering instead of a fully unified record-detail shell.
- Jobs and worker operations are more mature now, but their archive lifecycle is still lighter than the product / supplier registry archive model.
- Compatibility-only internal names from the old client-era data model still exist and should only be removed in a dedicated migration pass.
