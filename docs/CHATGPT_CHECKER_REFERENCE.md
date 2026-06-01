# MandiTrade Checker Reference

Generated from the current repository state on 2026-06-01 after the Mandi Order timeline and supply-flow usability pass.

## Mandi Order Timeline Status

- `Mandi Orders` now exposes a role-safe visual timeline for the admin-managed supply flow in [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py).
- Timeline steps now explicitly render:
  - `Manufacturer Requested`
  - `Admin Reviewing`
  - `Sent To Mahajan`
  - `Mahajan Quoted`
  - `Admin Price Set`
  - `Manufacturer Confirmed`
  - `Mahajan Dispatched`
  - `Manufacturer Received`
  - `Closed`
- Timeline rendering now uses the shared component in [components/order_timeline.py](/c:/2026/manditrade/manditrade/components/order_timeline.py) with custom mandi labels.
- Every order detail view now shows:
  - order ID
  - manufacturer
  - mahajan
  - raw material item summary
  - mahajan price
  - manufacturer price
  - admin earning
  - supply-ledger and mandi-ledger status
  - current status
  - timeline
  - next action

## Role Action Status

- `platform_admin`
  - assign mahajan from manufacturer requests
  - set downstream manufacturer price from mahajan quotes
  - close received mandi orders
  - cancel open mandi orders
- `mahajan`
  - submit quote only for assigned `Sent To Mahajan` orders
  - dispatch only for `Manufacturer Confirmed` orders
- `manufacturer`
  - create raw-material supply request
  - confirm only admin-priced orders
  - mark received only after mahajan dispatch

Role-to-action scoping is enforced in the current UI helper flow inside [modules/procurement/dashboard.py](/c:/2026/manditrade/manditrade/modules/procurement/dashboard.py) and backed by transaction checks in [services/procurement_transaction_service.py](/c:/2026/manditrade/manditrade/services/procurement_transaction_service.py).

## Raw Material vs Product Separation Status

- `Raw Materials` is explicitly framed as the mahajan/admin supply-input layer in [modules/raw_materials/dashboard.py](/c:/2026/manditrade/manditrade/modules/raw_materials/dashboard.py).
- `Products` is explicitly framed as the finished-product selling layer in [modules/products/dashboard.py](/c:/2026/manditrade/manditrade/modules/products/dashboard.py).
- `Mandi Orders` now reinforces that raw materials belong to supply procurement while finished products belong to catalog/client/marketplace selling.
- No RBAC changes were introduced in this usability pass.

## Dashboard Card Status

- `Mandi Orders` now includes clickable dashboard cards for:
  - `Open Requests`
  - `Awaiting Mahajan Quote`
  - `Awaiting Manufacturer Confirmation`
  - `Dispatched`
  - `Received`
  - `Closed`
- These cards now filter the `Orders` tab dataset through shared page-state helpers in [utils/page_ui.py](/c:/2026/manditrade/manditrade/utils/page_ui.py).

## Transaction Flow Status

- Admin-managed mahajan supply workflow remains intact:
  - manufacturer request
  - admin assignment
  - mahajan quote
  - admin pricing
  - manufacturer confirmation
  - mahajan dispatch
  - manufacturer receipt
  - admin close
- Supply orders can now also be cancelled by admin before receipt.
- Dual ledger behavior remains:
  - `Supply Ledger` for `Admin <-> Mahajan`
  - `Mandi Ledger` for `Admin <-> Manufacturer`

## Tests Result

- `python -m pytest tests/ -q`
  - Passed: `159`
  - Skipped: `5`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts`
  - Passed
- `python -c "import app; print('app import ok')"`
  - Passed

Additional coverage now checks:

- mandi timeline statuses are complete
- role-specific mandi actions are scoped correctly
- order-detail payload contains the required business fields
- dashboard-card status filters work
- raw-material and finished-product labels stay separate
- mandi RBAC still blocks wrong roles
- admin cancel and close actions persist correctly
