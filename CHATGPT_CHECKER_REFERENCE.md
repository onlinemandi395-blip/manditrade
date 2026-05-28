# MandiTrade Checker Reference

## Purpose
Use this file as restart context for a fresh LLM session acting as checker/reviewer on the current MandiTrade workspace.

## Product Identity
MandiTrade is now aligned to:

`Digital Bharat Mandi + Khata + RFQ + Inventory + Jobs Network`

It should not drift back toward:
- agreement-heavy ERP
- agreement PDFs
- settlement-engine-first workflow
- mock login paths
- ecommerce checkout framing

## Active Navigation Model
- `Dashboard`
- `My Actions`
- `Notifications`
- `Products`
- `Inventory`
- `Client Orders`
- `Mandi RFQ`
- `Ledger / Khata`
- `Payments`
- `Dispatch`
- `Clients`
- `Jobs in Mandi`
- `Workers`
- `Manufacturer Onboarding`
- `System Health`

### Visibility Rules
- `System Health`: platform admin only
- `Manufacturer Onboarding`: platform admin only
- `Jobs in Mandi`: manufacturers, admin-as-manufacturer, worker-enabled client, worker role
- `Workers`: manufacturers, admin-as-manufacturer, worker-enabled client, worker role

## Active Domain In Code
- Product proposal and admin approval flow with `mandi_price` and `mrp`
- Dual inventory:
  - `self_inventory`
  - `mandi_inventory`
- Self-to-mandi transfer
- Mandi-to-self withdraw
- Multi-product client orders
- Client payment proposals
- RFQ creation and response workflow
- Trade confirmation records instead of agreement lifecycle
- Bilateral ledger / khata
- Gmail ledger reminders
- In-app notifications
- My Actions aggregation
- Manufacturer onboarding workflow
- Jobs marketplace
- Worker profiles and job applications

## Jobs In Mandi Module
### Services
- [services/job_service.py](C:/2026/manditrade/manditrade/services/job_service.py)
- [services/worker_service.py](C:/2026/manditrade/manditrade/services/worker_service.py)

### Pages
- [modules/jobs/dashboard.py](C:/2026/manditrade/manditrade/modules/jobs/dashboard.py)
- [modules/workers/dashboard.py](C:/2026/manditrade/manditrade/modules/workers/dashboard.py)

### Current Flow
1. Manufacturer posts job
2. Worker profile sees open jobs
3. Worker applies with note
4. Manufacturer updates application status
5. Gmail queue and in-app notifications are triggered
6. If payment remains unpaid on completion, ledger entry can be created

## UI Upgrade
### Shared UI Components
- [components/html_renderer.py](C:/2026/manditrade/manditrade/components/html_renderer.py)
- [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py)
- [components/three_d_cards.py](C:/2026/manditrade/manditrade/components/three_d_cards.py)
- [components/responsive_layout.py](C:/2026/manditrade/manditrade/components/responsive_layout.py)
- [assets/styles/manditrade_3d.css](C:/2026/manditrade/manditrade/assets/styles/manditrade_3d.css)

### Visual Direction
- dark premium background
- animated radial gradients
- glass panels
- 3D cards
- hover lift
- responsive metric grids
- mobile-first single column collapse

### Pages Already Upgraded
- Dashboard variants
- My Actions
- Notifications
- Products
- Inventory
- Client Orders
- Mandi RFQ
- Ledger / Khata
- Payments
- Dispatch
- Clients
- Jobs in Mandi
- Workers
- Manufacturer Onboarding
- Admin dashboard

## Important Files
- App shell:
  - [app.py](C:/2026/manditrade/manditrade/app.py)
  - [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py)
  - [bootstrap/service_container.py](C:/2026/manditrade/manditrade/bootstrap/service_container.py)
- Core services:
  - [services/order_transaction_service.py](C:/2026/manditrade/manditrade/services/order_transaction_service.py)
  - [services/procurement_transaction_service.py](C:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [services/dual_inventory_service.py](C:/2026/manditrade/manditrade/services/dual_inventory_service.py)
  - [services/ledger_service.py](C:/2026/manditrade/manditrade/services/ledger_service.py)
  - [services/ledger_reminder_service.py](C:/2026/manditrade/manditrade/services/ledger_reminder_service.py)
  - [services/notification_center_service.py](C:/2026/manditrade/manditrade/services/notification_center_service.py)
  - [services/action_center_service.py](C:/2026/manditrade/manditrade/services/action_center_service.py)
  - [services/manufacturer_onboarding_service.py](C:/2026/manditrade/manditrade/services/manufacturer_onboarding_service.py)
  - [services/security_service.py](C:/2026/manditrade/manditrade/services/security_service.py)

## Admin Identity Notes
- OAuth still remains Google Sign-In only
- `platform_admin` is determined by configured admin email
- Sidebar/admin capability checks use `security_service.is_admin_identity(current_user)`
- First-time admin runtime unlock is bootstrap verification + vault-backed reuse

## What Was Removed Or Deprecated From Active Path
- agreement lifecycle as required business gate
- agreement PDF dependency
- settlement-engine-first workflow
- old mock/demo-first identity assumptions

Legacy agreement-era files may still exist on disk, but they should not be treated as active workflow.

## Verification Snapshot
- `python -m pytest tests/` -> `29 passed, 5 skipped`
- `python -m compileall app.py modules services utils components schemas bootstrap scripts` -> success
- `python -c "import app; print('app import ok')"` -> success

## Current Known Gaps / Risks
- Pure `platform_admin` sessions do not yet have a polished explicit impersonation toggle into manufacturer mode
- Some non-primary pages may still rely more on Streamlit tables than custom mobile cards
- Deployed Streamlit app can lag local workspace and create false RBAC/debug signals
- Legacy agreement-era files still need a final cleanup pass if full removal is required

## Exact Next 3 Actions
1. Validate deployed Streamlit app is serving the latest workspace and showing the updated build marker and role-aware nav.
2. Add explicit admin-as-manufacturer session switch if product wants platform admin to use manufacturer pages without manual context mapping.
3. Do a final inactive agreement-module cleanup pass and remove any remaining dead references after deployment validation.
