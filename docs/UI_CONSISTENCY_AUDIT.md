# UI Consistency Audit

Generated on 2026-06-03 during the second-wave design-system rollout.

Status meanings:

- `MIGRATED`
- `PARTIAL`
- `LEGACY_UI`
- `SKIP_FOR_NOW`

## Medium-Traffic Screens

- `modules/marketplace/dashboard.py`
  - `PARTIAL`
  - platform shell and KPI cards adopted
  - card shopping flow remains intentionally custom
- `modules/raw_materials/dashboard.py`
  - `PARTIAL`
  - platform shell, KPI cards, data grid, and entity form adopted
  - preview cards still coexist with tabular registry
- `modules/suta_mandi/dashboard.py`
  - `PARTIAL`
  - platform shell, KPI cards, and data grid adopted
  - request-cart card flow remains custom by design
- `modules/jobs/dashboard.py`
  - `LEGACY_UI`
  - still uses older page header / metric grid / panel pattern
  - candidate for next safe migration batch
- `modules/notifications/dashboard.py`
  - `LEGACY_UI`
  - functionally rich but still uses older shell/layout primitives
  - should migrate after jobs because admin notification console is dense
- `modules/ledger/dashboard.py`
  - `LEGACY_UI`
  - finance readability is good, but shell/grid adoption is incomplete
- `modules/admin/manufacturers.py`
  - `LEGACY_UI`
  - CRUD stable, design-system migration still pending
- `modules/admin/mahajans.py`
  - `LEGACY_UI`
  - CRUD stable, design-system migration still pending
- `modules/admin/packaging_services.py`
  - `LEGACY_UI`
  - forms and registry still use older layout pattern
- `modules/admin/courier_services.py`
  - `LEGACY_UI`
  - forms and registry still use older layout pattern
- `modules/logistics/dashboard.py`
  - `PARTIAL`
  - platform shell, KPI cards, and data grid adopted
- `modules/profile/dashboard.py`
  - `LEGACY_UI`
  - multi-role forms remain on older shell pattern
  - should migrate carefully because of many role branches
- `modules/access/dashboard.py`
  - `PARTIAL`
  - public landing now uses shared shell/KPI framing
  - remains intentionally separate from private navigation

## First-Wave Pages

- `modules/admin/operations_dashboard.py`
  - `MIGRATED`
- `modules/admin/finance_operations.py`
  - `MIGRATED`
- `modules/procurement/dashboard.py`
  - `MIGRATED`
- `modules/products/dashboard.py`
  - `MIGRATED`
- `modules/public_orders/dashboard.py`
  - `MIGRATED`
- `modules/payments/dashboard.py`
  - `MIGRATED`
- `modules/analytics/dashboard.py`
  - `MIGRATED`

## Shared Component Audit

- page hero usage
  - strong on first-wave pages
  - partial on second-wave pages via platform shell
- KPI card usage
  - strong on first-wave pages
  - partial on marketplace, raw materials, suta mandi, logistics, access
- data grid usage
  - strong on first-wave pages
  - added on raw materials, suta mandi, logistics
- empty state usage
  - broadly present
  - still mixed between legacy and new shared blocks
- status chip usage
  - available in shared layer
  - not yet fully enforced across all legacy admin screens
- detail drawer usage
  - shared entry point exists
  - adoption still limited
- design tokens usage
  - active globally through shell CSS loading
- responsive safety
  - improved on shell-adopted pages
  - older dense admin CRUD screens still need follow-up

## Skip For Now

- deeply branched role-specific profile forms
- dense notification console internals
- jobs lifecycle management surface

These are stable and should migrate only in smaller focused passes.
