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

## Bulk Action Model

- shared selection/action surface now exists in:
  - `components/bulk_actions.py`
- current bulk-service execution lives in:
  - `services/bulk_action_service.py`
- current safe first-wave actions include:
  - bulk mark read
  - bulk mark resolved
  - bulk retry failed email queue items
  - bulk export from adopted operational pages

## Background Task Model

- lightweight task tracking now exists in:
  - `services/background_task_service.py`
  - `components/background_tasks_panel.py`
- current tracked task areas include:
  - search rebuild
  - KPI refresh
  - alert refresh
  - overdue refresh
  - canonical validation
  - cutover readiness generation

## Recovery Action Model

- admin-safe recovery orchestration now exists in:
  - `services/recovery_action_service.py`
- command palette and System Health can now trigger:
  - retry failed email queue
  - rebuild search index
  - refresh KPI snapshot
  - regenerate alerts
  - rerun canonical validation
  - refresh overdue detection
  - generate cutover readiness report

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
  - direct bulk-action implementations outside the shared layer
  - raw background-task writes outside the task service
  - retry/recovery logic outside the shared recovery service

## Commerce Guardrails

- commerce-focused heuristics now also flag:
  - raw commerce tables on refined commerce pages
  - missing shared image fallback usage
  - missing empty-state usage on commerce pages
  - hardcoded commerce status-color patterns
  - direct image rendering that bypasses shared card/detail helpers
