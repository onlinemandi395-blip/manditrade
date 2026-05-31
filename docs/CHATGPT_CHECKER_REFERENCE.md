# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the single unified login and role-redirect pass.

## Single Login Page Status

- The app now uses one canonical login renderer in [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py).
- Google Sign-In is the only login action.
- No marketplace-specific login or dashboard-specific login entry remains.

## Duplicate Login Removal Status

- Marketplace no longer renders a separate public-buyer sign-in CTA.
- Unauthenticated Dashboard and Marketplace routes both render the same global login page through centralized route handling in [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- The sidebar auth panel no longer suggests separate marketplace browsing/login behavior.

## Role-Based Landing Status

- After Google OAuth, role resolution still runs through:
  - admin email from config/secrets
  - manufacturer registry
  - manufacturer client registry
  - public buyer registry
  - worker registry
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
  - Unknown -> pending/access-mapping flow

## Marketplace Login Unification Status

- Marketplace is not a separate login system.
- Unauthenticated marketplace access now routes to the same global login page.
- Public buyer creation remains driven by the same Google OAuth flow and role resolver rather than a separate marketplace auth surface.

## Dashboard Login Unification Status

- Dashboard is not a separate login system.
- Unauthenticated dashboard access routes to the same global login page.
- Centralized `can_access_route(...)` now applies route access logic instead of page-by-page login branching.

## SuperUser / RBAC Status

- SuperUser base authority and context-switch behavior remain active from the previous pass.
- Normal users remain restricted to their own route groups.
- SuperUser privacy boundary for other manufacturers' private client identities remains intact.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blockers

- The compatibility label `platform_admin` still remains in code and data structures instead of a fully normalized `SUPERUSER` constant.
- Unknown user post-login flow still lands on pending/access mapping unless the role resolver has a marketplace/public-buyer hint, so broader self-serve onboarding design remains a product decision rather than a login-system blocker.
