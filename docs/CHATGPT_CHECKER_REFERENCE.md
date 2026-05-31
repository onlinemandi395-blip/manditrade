# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the final navigation and RBAC normalization pass.

## Normalized Navigation Status

- Navigation is now centralized through [services/navigation_service.py](C:/2026/manditrade/manditrade/services/navigation_service.py) using `ROLE_NAVIGATION_MAP`.
- Sidebar rendering in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py) now groups sections visually instead of scattering role navigation logic across modules.
- Navigation terminology is now aligned to the final product layers:
  - `Marketplace`
  - `Marketplace Orders`
  - `Mandi Network`
  - `Mandi Orders`
  - `RFQ`
  - `Payments`
  - `Ledger`
  - `Platform Commission`

## Role Navigation Matrix

- `platform_admin` / SuperUser:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Marketplace`
  - `Marketplace Orders`
  - `Mandi Network`
  - `RFQ`
  - `Mandi Orders`
  - `Manufacturers`
  - `Products`
  - `Product Approvals`
  - `Payments`
  - `Ledger`
  - `Platform Commission`
  - `Jobs`
  - `System Health`
- `manufacturer`:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Products`
  - `Inventory`
  - `Clients`
  - `Client Orders`
  - `Ledger`
  - `Marketplace`
  - `Marketplace Orders`
  - `Mandi Network`
  - `RFQ`
  - `Mandi Orders`
  - `Payments`
  - `Jobs`
- `client`:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Products`
  - `My Orders`
  - `Ledger`
  - `Payments`
- `public_buyer`:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Marketplace`
  - `Marketplace Orders`
  - `Jobs`
- `worker`:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Marketplace`
  - `Marketplace Orders`
  - `Jobs`

## Naming Cleanup Status

- Old or mixed labels are removed from normalized navigation:
  - `Mandiplace`
  - `Mandiplace Orders`
  - lowercase `rfq`
  - `Commission Summary`
  - `Public Orders` as a primary nav label
- [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py) now maps normalized labels onto existing working modules and summary surfaces.

## RBAC Normalization Status

- RBAC continues to work centrally through [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- Key protections remain intact:
  - public buyers cannot access RFQ
  - clients cannot access inventory
  - workers cannot access payments
  - manufacturers cannot access System Health
  - SuperUser can access all normalized sections
- SuperUser context switching still works, but navigation stays normalized from the SuperUser base role.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blocker

- Some legacy internal route and module names still exist behind the normalized labels for compatibility, but user-facing navigation and RBAC terminology are now aligned to the final product structure.
