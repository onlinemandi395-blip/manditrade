# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-01 after the RBAC redefinition, route cleanup, and navigation normalization pass.

## Final Role Model

- `platform_admin`
  - Platform governance only.
  - Navigation includes `Manufacturers`, `Mahajans`, `Products`, `Product Approvals`, `Marketplace`, `Marketplace Orders`, `Mandi Orders`, `Payments`, `Ledger`, `Platform Commission`, `Jobs`, `System Health`, and `Analytics`.
  - Route guard no longer treats platform admin as a blanket bypass for non-admin pages.
- `mahajan`
  - Admin-linked supply role.
  - Navigation includes `Raw Materials`, `Mandi Orders`, `Payments`, `Ledger`, and `Jobs`.
  - Marketplace, manufacturers, clients, and platform health stay blocked.
- `manufacturer`
  - Private seller/operator role.
  - Navigation includes `Products`, `Inventory`, `Clients`, `Client Orders`, `Marketplace`, `Marketplace Orders`, `Mandi Orders`, `Payments`, `Ledger`, and `Jobs`.
  - Does not expose `Manufacturers`, `Platform Commission`, or `System Health`.
- `client`
  - Private buyer under one manufacturer.
  - Navigation includes `Products`, `Client Orders`, `Payments`, and `Ledger`.
  - Marketplace admin and mandi-network routes stay blocked.
- `public_buyer`
  - Public marketplace role.
  - Navigation includes `Marketplace`, `Marketplace Orders`, and `Jobs`.
  - No client-order, mandi-order, or ledger access.
- `worker`
  - Workforce role.
  - Navigation is limited to `Jobs` plus shared account pages.

## Final Navigation Map

- Navigation is centralized in [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py).
- `ROLE_NAVIGATION_MAP` is now the only source of truth for role menus.
- Pre-login navigation is limited to `Dashboard`.
- The sidebar session area remains the only place where Google sign-in is rendered.
- Legacy labels are normalized through `NAV_ALIAS_MAP`.
  - `Mandiplace` -> `Mandi Orders`
  - `Mandiplace Order` -> `Mandi Orders`
  - `rfq` / `RFQ` -> `Mandi Orders`
  - `Marketplace Order` -> `Marketplace Orders`
  - `Platform Commision` -> `Platform Commission`

## Route Guard Status

- Central guard remains in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- `can_access_route(user, route)` now normalizes aliases before permission checks.
- Unauthenticated access resolves to the public landing flow and does not expose marketplace navigation before login.
- Blocked routes render a clean access-denied status page instead of debug text or sidebar-only hiding.
- Route access is now strict by role:
  - `platform_admin` -> admin governance routes only
  - `mahajan` -> supply routes only
  - `manufacturer` -> manufacturer routes only
  - `client` -> client routes only
  - `public_buyer` -> public marketplace routes only
  - `worker` -> worker routes only

## Mahajan Role Status

- `mahajan` is now a first-class supported role in:
  - [services/auth_service.py](/c:/2026/manditrade/manditrade/services/auth_service.py)
  - [services/access_portal_service.py](/c:/2026/manditrade/manditrade/services/access_portal_service.py)
  - [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py)
  - [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py)
  - [modules/mahajan/dashboard.py](/c:/2026/manditrade/manditrade/modules/mahajan/dashboard.py)
- Current implementation supports admin-reviewed activation through the access-request flow.
- Manufacturer-to-mahajan direct routing remains blocked.

## Manufacturer / Client Separation Status

- Manufacturer navigation includes `Clients` and `Client Orders`.
- Manufacturer navigation does not include `Manufacturers`.
- Manufacturer route access to manufacturer registry pages remains blocked.
- Client management remains manufacturer-scoped in [modules/clients/dashboard.py](/c:/2026/manditrade/manditrade/modules/clients/dashboard.py).
- Existing tests continue to verify:
  - create client
  - edit own client
  - deactivate own client
  - Gmail invite
  - own-client privacy boundaries

## RFQ To Mandi Orders Terminology Status

- RFQ is no longer primary user-facing navigation.
- User-facing route normalization now resolves RFQ-style labels to `Mandi Orders`.
- Internal procurement/RFQ code paths remain in place for compatibility where needed.
- Public landing copy now refers to mandi orders instead of RFQ-first wording.

## Ledger Scope Status

- Navigation label remains `Ledger`.
- Visibility remains role-scoped:
  - `platform_admin` sees supervisory ledger summaries only through admin views.
  - `mahajan` sees own supply-finance route surface.
  - `manufacturer` sees manufacturer ledger routes.
  - `client` sees client ledger routes only.
  - `public_buyer` and `worker` remain blocked from ledger routes.
- Existing privacy tests continue to enforce hiding private notes and commission internals from client views.

## Pricing Visibility Status

- Product pricing visibility remains centralized in [services/product_catalog_service.py](/c:/2026/manditrade/manditrade/services/product_catalog_service.py).
- Role visibility now aligns as follows:
  - `platform_admin` -> full pricing visibility
  - `manufacturer` -> full allowed pricing visibility
  - `client` -> `client_price` only via `your_price`
  - `public_buyer` -> `marketplace_price` only via `price`
  - `mahajan` -> supply-facing `mandi_price` via `supply_price`

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `145`
  - Skipped: `5`
- RBAC coverage includes:
  - exact navigation expectations by role
  - pre-login sidebar restrictions
  - alias normalization to `Mandi Orders`
  - manufacturer/client privacy separation
  - mahajan activation and route restrictions
  - role-based pricing visibility

## Remaining Blockers

- Mahajan is now role-wired, but the current UI is still a scoped supply dashboard placeholder rather than a full raw-material operations suite.
- Internal RFQ/procurement service naming remains in legacy code for compatibility, even though user-facing navigation now presents `Mandi Orders`.
