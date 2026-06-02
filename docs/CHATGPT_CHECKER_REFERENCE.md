# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-02 after the final RBAC and commerce rule-freeze pass.

## Final Decision Matrix

- SuperUser context switch: enabled
- Platform Mode and Admin Manufacturer Mode: separated
- Platform admin physical inventory: not defaulted
- Admin role: orchestration, supervision, approvals, logistics, commission visibility
- Payments: collected directly by seller, manufacturer, or supplier
- Admin payment receiver behavior: not default
- Mandi Orders: admin-routed
- Direct manufacturer-to-mahajan ordering: blocked by model
- Direct manufacturer-to-manufacturer mandi ordering: not primary route
- Mandi quote model: one active supplier path at a time
- Delivery/logistics owner: `platform_admin`
- Public buyer to client conversion: supported by manufacturer invitation
- Client credit limit: supported
- Partial payments: supported
- Worker role: active and restricted

## SuperUser Context Switch Status

- Effective-role resolution remains centralized in [bootstrap/app_bootstrap.py](/c:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py) and [services/security_service.py](/c:/2026/manditrade/manditrade/services/security_service.py).
- `platform_admin` context remains governance-only and does not behave like a normal manufacturer workspace.
- Admin manufacturer context still behaves like a manufacturer workspace and keeps private client/inventory access scoped to the admin manufacturer code only.

## Admin Inventory / Orchestration Status

- No default platform-admin inventory model was added.
- Order and supply flows now treat admin as orchestrator rather than physical stock owner.
- Client/private inventory still belongs to manufacturer context only.
- Raw-material and mandi supply orchestration remains admin-controlled in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).

## Payment Recipient Model

- Public marketplace orders now store direct seller payment routing in [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py).
- Client orders now store manufacturer payment receiver metadata in [services/order_transaction_service.py](/c:/2026/manditrade/manditrade/services/order_transaction_service.py).
- Mandi supply ledgers now carry supplier-directed payment metadata in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).
- Payment UI copy in [modules/payments/dashboard.py](/c:/2026/manditrade/manditrade/modules/payments/dashboard.py) now reflects direct seller/supplier collection rather than admin collection.

## Admin Commission Model

- Pricing service now tags commission metadata with explicit commission status defaults in [services/pricing_service.py](/c:/2026/manditrade/manditrade/services/pricing_service.py).
- Commission summary now aggregates using current commission metadata and surfaces status counts in [modules/admin/commission_summary.py](/c:/2026/manditrade/manditrade/modules/admin/commission_summary.py).
- Supported modeled statuses now include:
  - `CALCULATED`
  - `DUE`
  - `PAID`
  - `WAIVED`
  - `DISPUTED`

## Admin-Routed Mandi Order Status

- Mandi Orders remain user-facing as `Mandi Orders`.
- Manufacturer requests are persisted as admin-routed supply orders.
- Mahajan assignment, pricing, downstream confirmation, and close/cancel remain admin-controlled.
- Current mandi detail pages and workflows remain centered in [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py).

## One-To-One Quote Status

- Each mandi order currently follows one active supplier path at a time.
- Current implemented supplier path is the mahajan-admin-manufacturer route.
- Multi-quote supplier competition is still not enabled.

## Admin Logistics Status

- Client orders, public orders, and mandi supply orders now all carry explicit logistics ownership metadata with `logistics_owner = platform_admin`.
- Mandi logistics update support was added in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).
- Client-order dispatch/delivery persistence now mirrors admin-owned logistics supervision in [services/order_transaction_service.py](/c:/2026/manditrade/manditrade/services/order_transaction_service.py).
- Public-order transition metadata now carries platform-owned logistics tracking in [services/public_order_service.py](/c:/2026/manditrade/manditrade/services/public_order_service.py).

## Public Buyer To Client Conversion Status

- Public buyer identity remains separate from manufacturer-specific client identity.
- Manufacturer invitation and client activation continue to work through [services/access_portal_service.py](/c:/2026/manditrade/manditrade/services/access_portal_service.py) and [services/client_service.py](/c:/2026/manditrade/manditrade/services/client_service.py).
- Public buyer marketplace history remains separate from private client order history.

## Credit Limit Status

- Client records already store `credit_limit` and now have credit summary helpers in [services/client_service.py](/c:/2026/manditrade/manditrade/services/client_service.py).
- Order confirmation now checks khata-style client credit exposure before confirming a client order when ledger terms are used in [services/order_transaction_service.py](/c:/2026/manditrade/manditrade/services/order_transaction_service.py).
- Credit summary now supports:
  - `credit_limit`
  - `current_outstanding`
  - `available_credit`
  - `credit_status`

## Partial Payment Status

- Ledger entries now support:
  - `PENDING`
  - `PARTIAL`
  - `PAID`
  - `OVERDUE`
  - `DISPUTED`
- Payment records now include `payment_id`, paid amount, remaining due, note, and timestamp in [services/ledger_service.py](/c:/2026/manditrade/manditrade/services/ledger_service.py).
- Ledger dashboard now treats partial balances as active outstanding items in [modules/ledger/dashboard.py](/c:/2026/manditrade/manditrade/modules/ledger/dashboard.py).

## Worker Role Status

- Worker navigation remains active and limited to:
  - `Dashboard`
  - `My Profile`
  - `Notifications`
  - `My Actions`
  - `Jobs`
- Worker payment, ledger, client, inventory, mandi, and commission access remain blocked by route guards and navigation scoping.

## Navigation Status

- Final role-aware navigation is still centralized in [services/navigation_service.py](/c:/2026/manditrade/manditrade/services/navigation_service.py).
- Route enforcement remains centralized in [bootstrap/route_registry.py](/c:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- One extra manufacturer-specific shopping page, `Suta Mandi`, is still present because it was explicitly added later as a specialized manufacturer raw-material market.

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `173`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

## Remaining Blockers

- The manufacturer-supplier admin-routed mandi path is not yet fully implemented as a first-class alternative to the mahajan supply path; the current operational route is still mahajan-centric.
- Commission lifecycle actions such as manual `WAIVED` and `DISPUTED` transitions are modeled in data/status expectations but do not yet have a dedicated admin workflow surface.
- `Suta Mandi` remains intentionally present as a manufacturer-only specialized raw-material market, which is slightly beyond the frozen base navigation list but consistent with later confirmed product direction.
