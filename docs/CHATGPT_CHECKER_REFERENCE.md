# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the public buyer first-login onboarding polish pass.

## Pre-Login Navigation Cleanup Status

- Unauthenticated navigation now resolves to `Access` only in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py).
- `Marketplace` and `Dashboard` are no longer shown as separate pre-login homepage/sidebar destinations.
- Unauthenticated route access still renders the same central login page through [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py).

## Single Login / RBAC Flow Status

- The app keeps one canonical login renderer in [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py).
- Google Sign-In remains the only login action.
- No marketplace-specific login or dashboard-specific login entry remains.

## Public Buyer First-Login Onboarding Status

- After Google OAuth, role resolution still runs through:
  - admin email from config/secrets
  - manufacturer registry
  - manufacturer client registry
  - public buyer registry
  - worker registry
- If a Google user is not found in admin/manufacturer/client/worker mappings, the resolver now defaults them into `public_buyer` via [services/access_portal_service.py](C:/2026/manditrade/manditrade/services/access_portal_service.py).
- First-time public buyers are now gated through profile completion before entering Marketplace in [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py).
- Returning public buyers with complete profiles go directly to Marketplace.
- Unknown Google users now fall back to `public_buyer` by default instead of `pending_user`.

## Public Buyer Profile Model

- Public buyer profiles are now maintained through [services/public_buyer_service.py](C:/2026/manditrade/manditrade/services/public_buyer_service.py) with fields including:
  - `full_name`
  - `mobile`
  - `alternate_mobile`
  - `business_name`
  - `city`
  - `state`
  - `pin_code`
  - `delivery_address`
  - `landmark`
  - `preferred_payment_mode`
  - `delivery_instructions`
  - `profile_status`
- Unified session payload now carries:
  - `base_role`
  - `active_context`
  - `manufacturer_code`
  - `client_id`
  - `public_buyer_id`
  - `worker_id`
- Landing behavior remains:
  - SuperUser/Admin -> SuperUser Dashboard
  - Manufacturer -> Manufacturer Dashboard
  - Client -> Client Dashboard
  - Public Buyer -> Marketplace
  - Worker -> Worker Dashboard

## Marketplace Login Unification Status

- Marketplace is not a separate login system.
- Unauthenticated marketplace access now routes to the same global login page.
- Marketplace appears only after login for public/default buyers.
- Incomplete public buyer profiles see a welcome/setup flow before product browsing and checkout.

## Dashboard Login Unification Status

- Dashboard is not a separate login system.
- Unauthenticated dashboard access routes to the same global login page.
- Centralized `can_access_route(...)` now applies route access logic instead of page-by-page login branching.

## Three-Price Product Rule Status

- Manufacturer product proposal continues to support:
  - `mandi_price`
  - `client_price`
  - `marketplace_price`
- Platform admin approval continues to support:
  - `approved_mandi_price`
  - `approved_client_price`
  - `approved_marketplace_price`
- Viewer pricing remains RBAC-scoped:
  - clients see `client_price`
  - public buyers see `marketplace_price`
  - manufacturers/admin can inspect allowed pricing fields

## SuperUser / RBAC Status

- SuperUser base authority and context-switch behavior remain active from the previous pass.
- Normal users remain restricted to their own route groups.
- SuperUser privacy boundary for other manufacturers' private client identities remains intact.

## Privacy / Storage Status

- Public buyer profiles remain stored in the dedicated public-buyer area and are not mixed into manufacturer private client registries.
- Public buyer profile data is used for public marketplace operations only.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blockers

- The compatibility label `platform_admin` still remains in code and data structures instead of a fully normalized `SUPERUSER` constant.
- Public buyer onboarding is now functional and validated, but richer welcome UX, address autofill, and progressive checkout nudges remain polish items rather than launch blockers.
