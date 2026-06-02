# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-02 after the client-system removal and 3-network cleanup pass.

## Final Role Model

- Active roles:
  - `platform_admin`
  - `manufacturer`
  - `mahajan`
  - `public_buyer`
  - `worker`
- Removed from live RBAC:
  - `client`

## Commerce Network Model

- `Marketplace`
  - public-buyer shopping lane
  - seller payout goes directly to manufacturer
- `MandiPlace`
  - manufacturer procurement / mandi-order lane
  - admin-routed supply workflow
- `Raw Materials`
  - admin + mahajan supply-management lane
  - manufacturers participate through admin-routed supply requests
- `Suta Mandi`
  - manufacturer-only specialized buying surface for suta / yarn supply
  - still fulfilled through admin + mahajan routing

## Navigation Status

- Navigation source of truth is centralized in [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py).
- Route enforcement is centralized in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- Final role-aware navigation now follows this shape:
  - `platform_admin`
    - `Dashboard`, `My Profile`, `Notifications`, `My Actions`, `Manufacturers`, `Mahajans`, `Products`, `Product Approvals`, `Marketplace`, `Marketplace Orders`, `MandiPlace`, `Mandi Orders`, `Raw Materials`, `Supply Orders`, `Payments`, `Ledger`, `Platform Commission`, `Jobs`, `System Health`, `Analytics`
  - `manufacturer`
    - `Dashboard`, `My Profile`, `Notifications`, `My Actions`, `Products`, `Inventory`, `Marketplace`, `Marketplace Orders`, `MandiPlace`, `Mandi Orders`, `Supply Requests`, `Suta Mandi`, `Payments`, `Ledger`, `Jobs`
  - `mahajan`
    - `Dashboard`, `My Profile`, `Notifications`, `My Actions`, `Raw Materials`, `Supply Orders`, `Payments`, `Ledger`, `Jobs`
  - `public_buyer`
    - `Dashboard`, `My Profile`, `Notifications`, `My Actions`, `Marketplace`, `Marketplace Orders`, `Jobs`
  - `worker`
    - `Dashboard`, `My Profile`, `Notifications`, `My Actions`, `Jobs`

## Access / Identity Status

- Google sign-in identity resolution is handled in [services/access_portal_service.py](/c:/2026/manditrade/manditrade/services/access_portal_service.py).
- Unknown Google users default to `public_buyer` when public auto-onboarding is enabled.
- `mahajan` remains admin-reviewed before operational access.
- SuperUser context switching remains active and effective-role resolution stays centralized in:
  - [bootstrap/app_bootstrap.py](/c:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [services/security_service.py](/c:/2026/manditrade/manditrade/services/security_service.py)

## Supply / Payment Status

- Mandi supply remains admin-routed in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).
- Direct manufacturer-to-mahajan ordering remains blocked by the live model.
- Public marketplace payments route directly to seller manufacturers in [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py).
- Supply orders route payment to the assigned mahajan and create:
  - manufacturer-side mandi ledger
  - governance-level supply ledger
- Logistics ownership remains `platform_admin` across marketplace and supply flows.

## Product / Price Visibility Status

- Product visibility remains role-scoped in [services/product_catalog_service.py](/c:/2026/manditrade/manditrade/services/product_catalog_service.py).
- Current effective price visibility:
  - `manufacturer` / `platform_admin`
    - mandi, B2B, and marketplace pricing visible
  - `mahajan`
    - supply-facing mandi price only
  - `public_buyer`
    - marketplace price only
- Raw material vs finished product separation is now reinforced in:
  - [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py)
  - [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)

## Legacy Compatibility Note

- Some internal data fields and helper services still carry legacy names such as `client_price` for backward-compatible pricing storage.
- The live navigation, route guards, sign-in resolution, and role-aware UI no longer expose a `client` role.

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `165`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

## Remaining Blockers

- Legacy folders and helper paths related to historical client-era flows still exist in the repo for compatibility, but they are no longer part of live RBAC.
- Some docs outside this checker reference still mention the previous client/private-order architecture and may need a separate content cleanup pass.
