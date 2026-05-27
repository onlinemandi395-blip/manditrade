# MandiTrade Checker Reference

## Active Product Model
MandiTrade is now operating as:

`Digital Bharat Mandi + Khata + RFQ + Inventory + Client Network`

The active business flow is:

1. Manufacturer or admin proposes a product.
2. Platform admin approves the product and sets `mandi_price` plus `mrp`.
3. Manufacturer manages dual inventory with `self_inventory` and `mandi_inventory`.
4. Client places a multi-product order with a payment proposal.
5. If self inventory is short, the platform creates a mandi RFQ.
6. Suppliers respond with freestyle trade terms.
7. Accepted orders and RFQs create lightweight trade confirmations.
8. Bilateral khata entries track due amount, paid amount, and balance.
9. Gmail queue sends ledger due reminders.
10. In-app notifications and My Actions aggregate pending work.

## Removed From Active Workflow
- Agreement PDFs
- Agreement lifecycle states
- Agreement settlement engine
- Agreement-heavy dashboard paths
- Agreement-required confirmation logic
- Mock login in active runtime flow
- Demo business workflow paths

## Added
- Dual inventory service with self/mandi reserve and transfer
- Multi-product client order flow with payment proposal
- Mandi RFQ workflow with supplier responses
- Trade confirmation JSON records
- Bilateral ledger / khata service
- Gmail ledger reminder orchestration with duplicate prevention
- In-app notification center
- Universal My Actions dashboard
- Admin-as-manufacturer compatible role handling

## Current Runtime Notes
- Google Sign-In remains the only active login path in app flow.
- Google Drive, Gmail runtime, SafeDriveWriteService, FileLockService, StartupRecoveryService, EventDispatcher, DeadLetterService, RuntimeMetricsService, service container, and system health remain in place.
- `System Health` stays admin-only in navigation.

## Remaining Blockers
- Some legacy agreement-era modules still exist on disk for backward compatibility, but they are not wired into active workflow.
- UI coverage is functional but still light in a few new sections; most domain completeness is currently enforced by services and tests.

## Test Results
- `python -m pytest tests/` -> `23 passed, 5 skipped`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts` -> success
- `python -c "import app; print('app import ok')"` -> `app import ok`

## Exact Next 3 Actions
1. Expand RFQ dashboard actions so buyers can accept responses directly from UI.
2. Add richer ledger payment-entry and adjustment forms in the Payments and Khata screens.
3. Remove or archive remaining unused agreement-era files after one more compatibility pass.
