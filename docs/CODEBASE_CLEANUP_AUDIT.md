# Codebase Cleanup Audit

Generated on 2026-06-03 during the lean cleanup + architecture consolidation pass.

## A. Safe To Remove

- `modules/client/__init__.py`
  - empty dead package stub
  - no runtime or test references found
- `modules/clients/__init__.py`
  - empty dead package stub
  - no runtime or test references found
- unused import in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py)
  - `render_rfq_summary_dashboard` was imported but not used

## B. Compatibility Required

- `services/client_service.py`
  - still used by tests and historical B2B/private-order compatibility
- `services/domain_paths_service.py`
  - still exposes `client_orders` and RFQ-era paths used by compatibility flows and tests
- legacy pricing fields:
  - `client_price`
  - `approved_client_price`
  - `suggested_client_price`
  - still required for compatibility-safe pricing and migration behavior
- RFQ aliases:
  - `RFQ -> Mandi Orders`
  - retained for navigation continuity and older references
- canonical/compatibility storage bridge:
  - `drive_path_service`
  - `storage_migration_service`
  - `storage_cutover_service`

## C. Refactor Candidates

- [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
  - mixes multiple registry domains and CRUD patterns
- [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - carries mandi supply, MandiPlace, logistics, and payment-proof behavior
- [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py)
  - shopping, payment proof, logistics, trust, and notifications in one service
- [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py)
  - large role-aware UI surface with many operational actions
- [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py)
  - mixed proposal, approval, and shopping-adjacent concerns

## D. Naming Inconsistencies

- canonical runtime role is `platform_admin`, but UI sometimes says `SuperUser`
- `client_price` family still exists although live UI now treats it as B2B pricing
- RFQ terminology still exists in compatibility paths and helper names
- `mandi_order`, `supply_order`, and `mandiplace_order` naming is business-correct but increases cross-service complexity

## E. Duplicate / Repeated Patterns

- repeated role string checks across route, security, and dashboard modules
- repeated payment status sets like `PENDING`, `PARTIAL`, `OVERDUE`
- repeated admin/manufacturer route gating
- repeated filter/export table patterns already partly reduced, but still present in several dashboards

## F. Cleanup Decisions In This Pass

- centralize canonical role constants
- centralize core payment/dispute status constants
- remove only obviously dead empty client package stubs
- remove one unused route import
- add architecture index and static health-check tooling
- keep compatibility-sensitive client, RFQ, and migration code intact

## Deferred Technical Debt

- full `client_price -> b2b_price` storage normalization should be a dedicated migration-safe pass
- service decomposition of governance/procurement/public-order layers should be incremental, not one-shot
- RFQ helper/storage naming can be normalized only after compatibility bridges are no longer needed
