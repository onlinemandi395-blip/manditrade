# MandiTrade Design System

This file is the current reference for the shared platform shell and UI composition rules.

## Goals

- make high-traffic operations pages feel like one product
- reduce page-to-page layout drift
- centralize visual tokens and status semantics
- improve responsive consistency without rewriting business logic

## Shell Model

- `components/platform_shell.py`
  - topbar
  - breadcrumbs
  - quick action chips
  - page hero handoff
- `components/page_hero.py`
  - title
  - subtitle
  - role badge
  - metrics
  - action chips
- `components/icon_sidebar.py`
  - compact route rendering with centralized icon labels

### Height Model

- app shell should honor viewport height with `min-height: 100vh`
- main app column should remain `height: auto`
- no page should depend on brittle fixed-height wrappers for normal content flow

### Scrolling Model

- the primary app column owns vertical growth
- forms, grids, and page sections should prefer natural height
- nested scrollbars should be avoided unless a component truly requires an isolated scroller

### Sidebar State Model

- navigation should preserve the active route
- transient sidebar UI should reset on:
  - route change
  - role/context switch
  - logout
  - deep-link redirect
- this lifecycle is centralized through `collapse_transient_sidebar_state()` in `services/session_state_service.py`

### Responsive Behavior Rules

- desktop keeps sidebar stable while content grows independently
- tablet/mobile should not trap users inside double-scroll layouts
- sidebar overlays and temporary sidebar states should collapse on navigation

Recommended page structure:

1. platform shell
2. KPI cards
3. tabs / filters / search
4. main content
5. detail drawer / timeline / action surface

## Design Tokens

- `assets/styles/design_tokens.css` is loaded before `assets/styles/manditrade_3d.css`
- token layer centralizes:
  - colors
  - spacing
  - radii
  - shadows
  - transitions
  - shell utility classes
  - compact density controls for cards, sidebar width, and KPI height

The existing 3D stylesheet remains the richer visual layer, while tokens define the reusable baseline.

## Shared Components

- `components/kpi_cards.py`
  - consistent KPI rendering wrapper
- `components/data_grid.py`
  - filter + export + pagination wrapper
- `components/detail_drawer.py`
  - reusable detail surface entry point
- `components/status_chip.py`
  - shared status visuals backed by `constants/statuses.py`
- `components/empty_state.py`
  - consistent empty-state CTA block
- `components/skeleton_loader.py`
  - lightweight loading placeholders
- `components/entity_form.py`
  - grouped form wrapper for shared layout
- `components/bulk_actions.py`
  - shared bulk-selection and action trigger surface
- `components/background_tasks_panel.py`
  - reusable background-task visibility panel

## Status Rules

- business statuses should come from `constants/statuses.py` where practical
- status visuals should not hardcode ad-hoc inline colors in module pages
- chips and badges should remain readable in dense admin/operator views

## Responsive Rules

- desktop first, but avoid horizontal overflow
- card stacks should collapse cleanly on tablet/mobile
- filters should wrap without hiding primary actions
- detail surfaces should remain readable before becoming more complex modal UX
- public product browsing should target:
  - 4-column desktop grid
  - 2-column tablet grid
  - 1-column mobile grid

## CSS Philosophy

- subtle motion only
- no repeated stylesheet injection
- gradients and glow are allowed, but should support operational clarity first
- tokens hold base values, feature CSS holds page-specific expression

## Current Adoption Pages

- `Operations Center`
- `Finance Operations`
- `Products`
- `Payments`
- `Marketplace Orders`
- `Mandi Orders / Procurement`
- `Analytics`
- `Marketplace`
- `Raw Materials`
- `Suta Mandi`
- `Logistics`
- `Public Access / Login`
- authenticated `Marketplace` for `public_buyer` now uses the compact product-browse-first landing treatment

## Audit Reference

- `docs/UI_CONSISTENCY_AUDIT.md`
  - tracks `MIGRATED`, `PARTIAL`, `LEGACY_UI`, and `SKIP_FOR_NOW`
  - keeps second-wave rollout incremental instead of forcing a one-shot UI rewrite

## Production Experience Layer

- `components/command_palette.py`
  - global navigation and search launcher
- `components/toast_manager.py`
  - unified feedback surface
- `components/error_boundary.py`
  - shared operator-safe failure surface
- `docs/PRODUCTION_EXPERIENCE.md`
  - operating model for productivity, recovery, and reliability UX
- `services/background_task_service.py`
  - lightweight task lifecycle tracking for recovery/export/operator actions
- `services/recovery_action_service.py`
  - centralized admin recovery orchestration

## Incremental Adoption Rule

Not every page must fully migrate in one pass.

Preferred order:

1. shell
2. hero
3. KPI cards
4. data grid
5. detail drawer
6. empty/loading states

## Testing Expectations

At minimum, changes to the design system layer should keep coverage for:

- shell rendering
- hero rendering
- status chip rendering
- detail drawer safety
- CSS injection deduplication
- route/page smoke stability
