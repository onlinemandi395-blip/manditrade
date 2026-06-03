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

## Status Rules

- business statuses should come from `constants/statuses.py` where practical
- status visuals should not hardcode ad-hoc inline colors in module pages
- chips and badges should remain readable in dense admin/operator views

## Responsive Rules

- desktop first, but avoid horizontal overflow
- card stacks should collapse cleanly on tablet/mobile
- filters should wrap without hiding primary actions
- detail surfaces should remain readable before becoming more complex modal UX

## CSS Philosophy

- subtle motion only
- no repeated stylesheet injection
- gradients and glow are allowed, but should support operational clarity first
- tokens hold base values, feature CSS holds page-specific expression

## Current First-Adoption Pages

- `Operations Center`
- `Finance Operations`
- `Products`
- `Payments`
- `Marketplace Orders`
- `Mandi Orders / Procurement`
- `Analytics`

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
