# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the strict navigation matrix and manufacturer clients bug fix pass.

## Strict Navigation Matrix Status

- Role navigation is now centralized through:
  - [services/navigation_service.py](C:/2026/manditrade/manditrade/services/navigation_service.py)
- `ROLE_NAVIGATION_MAP` now controls the final strict role views.
- Sidebar rendering in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py) now reads directly from the centralized role map and grouped navigation structure.

## Manufacturer Clients Bug Fix Status

- Manufacturer navigation now includes:
  - `Clients`
- Manufacturer navigation does not include:
  - `Manufacturers`
- Manufacturer role cannot access manufacturer registry or manufacturer CRUD routes.
- Manufacturer client management remains handled through:
  - [modules/clients/dashboard.py](C:/2026/manditrade/manditrade/modules/clients/dashboard.py)
- That page continues to support manufacturer-scoped:
  - create client
  - edit client
  - deactivate client
  - Gmail invite
  - client visibility restricted to own manufacturer workspace

## Platform Admin Manufacturer Page Status

- Manufacturer registry and manufacturer governance remain platform-admin owned through:
  - [modules/admin/manufacturers.py](C:/2026/manditrade/manditrade/modules/admin/manufacturers.py)
- Platform admin still supervises manufacturer activity without exposing raw private client detail in supervisor mode.

## Route Alias Compatibility Status

- Alias compatibility is now preserved through:
  - `NAV_ALIAS_MAP` in [services/navigation_service.py](C:/2026/manditrade/manditrade/services/navigation_service.py)
- Supported aliases include:
  - `MyProfile` -> `My Profile`
  - `Notification` -> `Notifications`
  - `My Action` -> `My Actions`
  - `Marketplace Order` -> `Marketplace Orders`
  - `Mandiplace` -> `Mandi Network`
  - `Mandiplace Order` -> `Mandi Orders`
  - `rfq` -> `RFQ`
  - `Payment` -> `Payments`
  - `Manufacturer` -> `Manufacturers`
  - `Product Approval` -> `Product Approvals`

## RBAC Enforcement Status

- RBAC enforcement remains centralized through:
  - [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py)
- Key strict checks now hold:
  - manufacturer can access `Clients`
  - manufacturer cannot access `Manufacturers`
  - public buyer cannot access `RFQ`
  - public buyer cannot access `Ledger`
  - worker cannot access `Payments`
  - client can access a safe `System Health` route that does not expose admin runtime diagnostics
  - platform admin can access all listed admin views

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blocker

- Some legacy internal modules still sit behind normalized labels and alias compatibility for stability, but the role matrix and manufacturer/client ownership rules are now centrally enforced.
