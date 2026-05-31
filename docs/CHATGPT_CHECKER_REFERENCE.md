# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-31 after the SuperUser context-switch pass.

## Admin / SuperUser Model Status

- Admin is now treated as one conceptual SuperUser account.
- Internal runtime label `platform_admin` still exists for compatibility.
- Base authority and UI context are separated:
  - `base_role` controls authority
  - `active_context` controls which dashboard/profile/workspace is rendered
- SuperUser can switch context across:
  - `Platform Admin`
  - `Manufacturer`
  - `Client`
  - `Public Buyer`
  - `Worker`

## Context Switcher Status

- Admin-only context switcher is available in the sidebar.
- Selected context is stored in session and serialized with the signed-in user payload.
- `ADMIN_MANU` is used as the private operating workspace when SuperUser previews manufacturer/client private flows.

## RBAC Rule Status

- SuperUser base authority can access all route groups even when UI is previewing a non-admin context.
- Normal users remain restricted to their assigned role surfaces only.
- SuperUser navigation now includes:
  - `Dashboard`
  - `My Profile`
  - `Products`
  - `Product Approvals`
  - `Manufacturers`
  - `Marketplace`
  - `Public Orders`
  - `Client Orders`
  - `RFQ`
  - `Inventory Summary`
  - `Commission Summary`
  - `Payments`
  - `Clients Preview`
  - `Ledger Summary`
  - `My Actions`
  - `Notifications`
  - `System Health`

## Privacy Boundary Status

- SuperUser supervisor mode remains aggregate-only for other manufacturers' private business.
- Supervisor surfaces do not expose:
  - client names
  - client emails
  - phone numbers
  - private ledger notes
  - private payment proposals
- Full private detail access is limited to `ADMIN_MANU` when the SuperUser is previewing manufacturer/client private operating context.

## Test Result

- `python -m pytest tests/ -q`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
- `python -c "import app; print('app import ok')"`

## Remaining Blockers

- The compatibility label `platform_admin` still remains in code and data structures instead of a fully normalized `SUPERUSER` constant.
- SuperUser analytics remain table-first operational summaries rather than richer reporting dashboards.
