# Architecture Index

Generated on 2026-06-03 as the current source-of-truth overview.

## Role Model

- `platform_admin`
- `manufacturer`
- `mahajan`
- `public_buyer`
- `worker`

Live RBAC no longer exposes `client`.

## Commerce Networks

- `Marketplace`
  - public-buyer shopping
  - direct seller payment to manufacturer
- `MandiPlace`
  - admin-routed manufacturer procurement
  - co-manufacturer supplier assignment
- `Raw Materials`
  - admin + mahajan supply layer
- `Suta Mandi`
  - manufacturer-only yarn/suta buying surface
  - fulfilled through admin + mahajan routing

## Storage Model

- compatibility mode remains default
- canonical Drive-style path model exists via:
  - [services/drive_path_service.py](/c:/2026/manditrade/manditrade/services/drive_path_service.py)
- migration/cutover services:
  - [services/storage_migration_service.py](/c:/2026/manditrade/manditrade/services/storage_migration_service.py)
  - [services/storage_cutover_service.py](/c:/2026/manditrade/manditrade/services/storage_cutover_service.py)
  - [services/canonical_storage_validation_service.py](/c:/2026/manditrade/manditrade/services/canonical_storage_validation_service.py)

## Order Flows

- Marketplace:
  - card browse -> cart -> checkout -> payment proof -> verification -> dispatch -> delivery
- Mandi supply:
  - manufacturer request -> admin assigns mahajan -> quote -> admin price -> manufacturer confirm -> dispatch -> receive
- MandiPlace:
  - manufacturer request -> admin assigns supplier manufacturer -> quote -> admin price -> packaging/courier -> confirm -> dispatch -> receive

## Supply Flows

- admin-routed only
- no direct manufacturer-to-mahajan bypass
- no direct manufacturer-to-manufacturer bypass in MandiPlace

## Notification Flows

- domain write -> audit/event -> in-app notification -> Gmail queue
- Gmail is queued, not sent directly from business modules
- deep links use:
  - [utils/deep_links.py](/c:/2026/manditrade/manditrade/utils/deep_links.py)

## Financial Flows

- finance transactions stored through:
  - [services/settlement_service.py](/c:/2026/manditrade/manditrade/services/settlement_service.py)
- invoices generated through:
  - [services/invoice_service.py](/c:/2026/manditrade/manditrade/services/invoice_service.py)
- disputes managed through:
  - [services/dispute_service.py](/c:/2026/manditrade/manditrade/services/dispute_service.py)
- finance console:
  - [modules/admin/finance_operations.py](/c:/2026/manditrade/manditrade/modules/admin/finance_operations.py)

## Logistics Flows

- logistics ownership remains platform-supervised
- marketplace logistics updates in:
  - [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py)
- MandiPlace courier + packaging in:
  - [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py)

## Migration Model

- dry-run first
- rehearsal before execute
- validation before cutover
- explicit operator switch from `compatibility` to `canonical`

## Current Cleanup Boundary

- compatibility-safe legacy fields and storage bridges remain intentionally preserved
- cleanup should reduce dead code and duplication without destabilizing migration safety
