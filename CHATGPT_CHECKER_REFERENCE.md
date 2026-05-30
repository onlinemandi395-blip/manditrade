# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the CSS-only futuristic UI upgrade pass.

## Current High-Signal Updates

- Existing Streamlit 3D shell was upgraded instead of replaced.
- UI remains CSS-only for animated 3D illusion layers.
- No backend business logic, auth flow, RBAC rules, Drive runtime, Gmail runtime, or transaction services were rewritten in this pass.
- Login page now has a stronger split premium surface:
  - brand-story glass panel
  - Google sign-in glass panel
  - animated mandi-grid / node illusion background
- Shared page hero bands are now richer and role-aware through the shell helper layer.
- Major workflow pages now inherit a more consistent futuristic glass system:
  - profile
  - products
  - product approvals
  - inventory
  - orders
  - RFQ
  - ledger
  - actions
  - notifications
  - system health

## UI Files Changed

- [assets/styles/manditrade_3d.css](C:/2026/manditrade/manditrade/assets/styles/manditrade_3d.css)
- [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py)
- [utils/ui_shell.py](C:/2026/manditrade/manditrade/utils/ui_shell.py)
- [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py)
- [modules/actions/dashboard.py](C:/2026/manditrade/manditrade/modules/actions/dashboard.py)
- [modules/admin/product_approvals.py](C:/2026/manditrade/manditrade/modules/admin/product_approvals.py)
- [modules/inventory/management.py](C:/2026/manditrade/manditrade/modules/inventory/management.py)
- [modules/ledger/dashboard.py](C:/2026/manditrade/manditrade/modules/ledger/dashboard.py)
- [modules/notifications/dashboard.py](C:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- [modules/products/dashboard.py](C:/2026/manditrade/manditrade/modules/products/dashboard.py)
- [modules/rfq/dashboard.py](C:/2026/manditrade/manditrade/modules/rfq/dashboard.py)
- [modules/system/health_dashboard.py](C:/2026/manditrade/manditrade/modules/system/health_dashboard.py)

## 3D CSS System Status

The active CSS shell now includes:

- animated gradient-mesh background
- subtle particle-dot field
- isometric floor/grid illusion
- floating translucent card/crate planes
- flowing line/triangle illusion layers
- glass haze and blur treatment
- sidebar glass navigation with active-state pills
- connected glass tabs with strong active state
- normalized button treatment
- focus-visible styling
- reduced-motion fallback

### Primary Reusable Visual Classes

- `.mt-glass-card`
- `.mt-hero-panel`
- `.mt-kpi-card`
- `.mt-action-card`
- `.mt-danger-card`
- `.mt-success-card`
- `.mt-market-card`
- `.mt-ledger-card`
- `.mt-rfq-card`
- `.mt-notification-card`
- `.mt-product-card`
- `.mt-surface-note`

## Login Page Status

Login page is now premium and Google-only.

### Active Structure

- left-side brand story panel
- right-side sign-in panel
- no mock login
- no role selector
- no onboarding token prompt
- same `Continue with Google` action remains active

### Files

- [modules/access/dashboard.py](C:/2026/manditrade/manditrade/modules/access/dashboard.py)
- [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py)
- [assets/styles/manditrade_3d.css](C:/2026/manditrade/manditrade/assets/styles/manditrade_3d.css)

## Dashboard Hero Status

Shared hero rendering was upgraded in [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py).

### Current Hero Features

- richer glow/orb/lane composition
- flowing overlay accent
- optional role chip
- optional metric strip in the hero band
- consistent futuristic kicker copy
- glass panel depth without JS

### Pages Using The Hero System

- login / pending access
- platform admin dashboard
- manufacturer dashboard
- client dashboard
- profile pages
- products
- product approvals
- inventory
- orders
- RFQ
- ledger
- actions
- notifications
- system health

## Role Pages Styled

### Platform Admin

- `Dashboard`
- `My Profile`
- `Products`
- `Product Approvals`
- `Manufacturers`
- `My Actions`
- `Notifications`
- `System Health`

### Manufacturer / Admin-as-Manufacturer

- `Dashboard`
- `My Profile`
- `Products`
- `Inventory`
- `Client Orders`
- `Mandi RFQ`
- `Ledger / Khata`
- `My Actions`
- `Notifications`

### Client

- `Dashboard`
- `My Profile`
- `Notifications`
- `Client Orders`
- `Ledger / Khata`

### Worker

- `Dashboard`
- `My Profile`
- `My Actions`
- `Notifications`
- `Jobs in Mandi`
- `Workers`

## Product / Approval UI Status

- Products page now has premium product-preview cards in addition to the registry table.
- Product approvals page now has a stronger approval-deck feel before the actual admin approval controls.
- Proposal comment thread and approval logic remain unchanged functionally in this pass.

## Actions / Notifications / RFQ / Ledger UI Status

### My Actions

- command-center note surface added
- high-priority mood strengthened by card styling
- full-width actions retained

### Notifications

- notification preview cards added
- unread vs resolved visual states added
- source/priority chips added
- runtime-delivery tab still documents immediate-send model

### RFQ

- negotiation-board framing added
- request lane and response lane now visually separated in overview

### Ledger / Khata

- remains intentionally calmer than other pages
- readability-first surface note added
- high-contrast KPI cards retained
- minimal-motion posture preserved

## Existing Business Features Still Active

These remain active and were not functionally altered by this UI pass:

- role-based `My Profile`
- manufacturer registry CRUD
- product proposal + approval
- approved product admin CRUD
- proposal comment thread
- runtime Gmail trigger without queue UI
- tabbed activity pages
- sidebar debug cleanup

## Accessibility / Performance Notes

### Accessibility

- visible focus ring styling added
- forms and tables remain Streamlit-native widgets
- no WebGL / heavy JS added
- reduced-motion mode disables animations/transitions
- ledger surfaces intentionally kept calmer for readability

### Performance

- CSS-only animation approach
- no external CDN dependency
- no Three.js/WebGL in this pass
- animations are slow ambient loops, not fast interactive motion

## Current Tests / Validation

### `python -m pytest tests/ -q`

```text
sssss...........................................................         [100%]
59 passed, 5 skipped in 9.58s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blockers

1. `admin_as_manufacturer` session-switch UX is still partial even though the role shape exists.
2. Orders / ledger / notification privacy still deserves a broader RBAC leak audit outside the latest UI work.
3. Shared-zone vs private-zone storage separation for inventory and orders is still incomplete.
4. RFQ response pricing validation remains a separate unresolved business-logic task.
5. Agreement-era legacy files still remain in the repository even though the active path no longer depends on them.

## Acceptance Snapshot

- futuristic CSS-only 3D shell: `DONE`
- premium Google login page: `DONE`
- consistent hero-band system: `DONE`
- glass styling on major role pages: `DONE`
- form readability preserved: `DONE`
- table readability preserved: `DONE`
- mock login absent: `DONE`
- tests passing: `DONE`
- app imports cleanly: `DONE`
