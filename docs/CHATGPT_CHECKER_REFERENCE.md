# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-01 after the admin-managed mahajan supply implementation.

## Supply Model

- `Mahajan` is the upstream raw-material supplier.
- `Platform Admin` controls the supply channel and sits between mahajan and manufacturer.
- `Manufacturer` requests mandi/raw-material orders only through admin.
- Manufacturers do not directly negotiate with mahajans inside the product workflow.

## Navigation And Route Status

- Central navigation remains defined in [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py).
- Sidebar route access remains centralized in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- `Mahajans` is now a dedicated admin page through [modules/admin/mahajans.py](/c:/2026/manditrade/manditrade/modules/admin/mahajans.py).
- `Raw Materials` is now a dedicated supply-catalog page through [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py).
- `Mandi Orders` now routes all allowed roles through the admin-managed supply workflow in [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py).

## Mandi Order Flow

One mandi transaction now follows this operational chain:

1. Manufacturer creates a supply request to admin.
2. Admin assigns the request to a mahajan.
3. Mahajan submits upstream quote pricing.
4. Admin sets downstream manufacturer pricing and fee mix.
5. Manufacturer confirms the admin-priced order.
6. Mahajan dispatches through the admin-controlled channel.
7. Manufacturer receives the shipment.

Supported internal statuses now include:

- `REQUESTED_BY_MANUFACTURER`
- `ADMIN_REVIEWING`
- `SENT_TO_MAHAJAN`
- `MAHAJAN_QUOTED`
- `ADMIN_PRICE_SET`
- `MANUFACTURER_CONFIRMED`
- `MAHAJAN_DISPATCHED`
- `MANUFACTURER_RECEIVED`
- `CLOSED`
- `CANCELLED`

## Pricing And Earnings

- Upstream mahajan quote is stored as `mahajan_unit_price`.
- Downstream manufacturer price is stored as `manufacturer_unit_price`.
- Supply earnings are computed in [services/pricing_service.py](/c:/2026/manditrade/manditrade/services/pricing_service.py) through `calculate_supply_commission(...)`.
- The commission object now tracks:
  - mahajan bill amount
  - manufacturer bill amount
  - gross spread
  - admin spread commission
  - remaining spread share
  - mahajan transaction fee
  - admin total earning

## Ledger Model

One confirmed mandi supply order now creates dual ledger legs:

- `Supply Ledger`
  - relationship: `Admin <-> Mahajan`
  - persisted through [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py)
- `Mandi Ledger`
  - relationship: `Admin <-> Manufacturer`
  - persisted through the existing ledger service with metadata scope `mandi_ledger`

Admin commission summary now also includes the supply channel through [modules/admin/commission_summary.py](/c:/2026/manditrade/manditrade/modules/admin/commission_summary.py).

## Role Coverage

- `platform_admin`
  - manages mahajan registry
  - assigns supply requests
  - sets downstream manufacturer price
  - monitors supply ledger, mandi ledger, payments, and aggregate commission
- `mahajan`
  - sees only admin-linked supply requests
  - manages own raw-material catalog
  - quotes assigned orders
  - dispatches confirmed orders
- `manufacturer`
  - creates supply requests
  - sees only own mandi orders
  - confirms admin-priced orders
  - marks dispatched shipments received

## Identity And Actions

- Access resolution now recognizes governance-backed mahajan records in [services/access_portal_service.py](/c:/2026/manditrade/manditrade/services/access_portal_service.py).
- Action center now exposes supply-specific actions for admin, manufacturer, and mahajan in [services/action_center_service.py](/c:/2026/manditrade/manditrade/services/action_center_service.py).

## Persistence Added

Governance-backed supply persistence now includes:

- `mahajans.json`
- `raw_materials.json`
- `supply_orders.json`
- `supply_ledgers.json`

These are managed by [services/governance_service.py](/c:/2026/manditrade/manditrade/services/governance_service.py).

## Verification

- `python -m pytest tests/test_pricing_engine.py tests/test_transactions.py tests/test_access_portal.py -q`
  - Passed: `38`
- `python -m compileall modules/procurement/dashboard.py modules/admin/mahajans.py modules/raw_materials/dashboard.py services/governance_service.py services/pricing_service.py services/procurement_transaction_service.py`
  - Passed

Full-suite verification should still be treated as the release gate after any adjacent UI or workflow edits.
