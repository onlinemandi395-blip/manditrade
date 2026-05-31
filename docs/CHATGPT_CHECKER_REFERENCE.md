# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the pre-login dashboard landing and top-nav Google login pass.

## Pre-Login Dashboard Navigation Status

- Unauthenticated navigation now resolves to `Dashboard` only in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py).
- `Marketplace` is no longer shown in the pre-login sidebar.
- `Access` is no longer shown as a separate pre-login destination.
- Unauthenticated users still reach one shared landing/login renderer through [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py) and [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py).

## Top-Nav Google Login Status

- Google Sign-In is now rendered from the top header bar in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py).
- The public landing body in [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py) no longer embeds a separate in-content login button.
- The header CTA styling is provided through:
  - [assets/styles/manditrade_3d.css](C:/2026/manditrade/manditrade/assets/styles/manditrade_3d.css)
  - `.mt-top-login-bar`
  - `.mt-google-login-btn`

## Same-Tab OAuth Link Status

- Pre-login Google Sign-In uses [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py) `render_same_tab_link_button(...)`.
- The link renders with `target="_self"` and does not use `_blank`.
- Header login URL generation still comes from the current OAuth runtime in [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py) via `build_authorization_url(...)`.
- Cloud fallback blockers and secrets warnings remain active, so staging cloud still refuses ambiguous local OAuth fallback.

## Public Landing / Marketplace Route Status

- Unauthenticated `Dashboard` opens the public landing dashboard.
- Unauthenticated `Marketplace` also resolves to that same landing/login experience instead of exposing a separate pre-login marketplace surface.
- Marketplace remains post-login only for public buyers and role-appropriate users.

## Public Buyer First-Login Status

- Unknown Google users still default into `public_buyer` through [services/access_portal_service.py](C:/2026/manditrade/manditrade/services/access_portal_service.py).
- First-time public buyers are still gated through profile completion before entering Marketplace in [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py).
- Returning complete public buyers still land directly in Marketplace.

## Post-Login RBAC Status

- Post-login RBAC behavior is unchanged by this pass.
- SuperUser context-switch behavior remains active.
- Manufacturers, clients, public buyers, and workers still receive only their allowed route groups after login.
- SuperUser privacy boundaries for other manufacturers' private clients remain intact.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blockers

- The compatibility runtime label `platform_admin` still remains in code and data structures instead of a normalized `SUPERUSER` constant.
- The public landing is now cleaner and more aligned with the login flow, but richer welcome UX and deeper marketing/explainer content are still polish items rather than RBAC blockers.
