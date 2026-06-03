# Production Experience

This document tracks the operator-facing productivity and resilience layer above core business workflows.

## Command Palette

- global command surface for fast navigation and record lookup
- keyboard focus target: `Ctrl/Cmd + K`
- route-aware and RBAC-aware
- backed by:
  - `components/command_palette.py`
  - `services/operational_search_service.py`

## Search Model

- command palette merges:
  - route shortcuts
  - operational search results
  - recent search memory
- current target areas:
  - orders
  - products
  - manufacturers
  - mahajans
  - payments
  - invoices
  - disputes
  - logistics

## Toast Model

- shared toast queue lives in:
  - `components/toast_manager.py`
- intended for:
  - success
  - warning
  - error
  - info
- meant to reduce scattered banner feedback over time

## Unsaved Changes Model

- scoped protection is handled through:
  - `services/session_state_service.py`
  - `components/entity_form.py`
- current behavior is intentionally conservative:
  - edit forms can register unsaved state
  - route and logout flows warn before context loss

## Recovery UX

- page-level failure isolation is handled through:
  - `components/error_boundary.py`
- current recovery surfaces emphasize:
  - retry
  - view details
  - system health repair actions

## Reliability Model

- reliability summary lives in:
  - `modules/system/health_dashboard.py`
- current summary areas:
  - failed tasks
  - queued retries
  - notification failures
  - stale locks
  - storage warnings

## Guardrails

- heuristic regression checks live in:
  - `scripts/codebase_health_check.py`
- current production-experience checks include:
  - raw feedback banners
  - direct exception rendering
  - duplicate search bars
  - inline color styles
  - repeated table patterns
