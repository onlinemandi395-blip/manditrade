# MandiTrade Checker Reference

## Purpose
This file is the compact checker reference for a fresh LLM session that must review, validate, and continue the current MandiTrade refactor without rediscovering the workspace from scratch.

## Current Repo State
- Repo: `https://github.com/onlinemandi395-blip/manditrade`
- Active branch: `main`
- Expected latest nav/build marker in app: `Build: 457c363`
- Local app entrypoint: [app.py](C:/2026/manditrade/manditrade/app.py)

## Active Product Model
MandiTrade is currently refactored toward:

`Digital Bharat Mandi + Khata + RFQ + Inventory + Client Network`

Not:
- agreement-heavy ERP
- PDF agreement workflow
- settlement-led formal agreement lifecycle

## Core Business Domain In Code
- Product governance and proposal/approval flow
- Dual inventory: `self_inventory` and `mandi_inventory`
- Multi-product client orders with payment proposals
- Mandi RFQ flow with supplier responses
- Trade confirmation JSON records
- Lightweight bilateral ledger / khata
- Gmail ledger reminder queueing
- In-app notifications
- Universal My Actions dashboard
- Admin manufacturer onboarding workflow with onboarding secret handoff
- One-time admin runtime vault setup

## Key Files
- Boot and routing:
  - [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
  - [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py)
  - [bootstrap/service_container.py](C:/2026/manditrade/manditrade/bootstrap/service_container.py)
- Domain services:
  - [services/order_transaction_service.py](C:/2026/manditrade/manditrade/services/order_transaction_service.py)
  - [services/procurement_transaction_service.py](C:/2026/manditrade/manditrade/services/procurement_transaction_service.py)
  - [services/dual_inventory_service.py](C:/2026/manditrade/manditrade/services/dual_inventory_service.py)
  - [services/ledger_service.py](C:/2026/manditrade/manditrade/services/ledger_service.py)
  - [services/ledger_reminder_service.py](C:/2026/manditrade/manditrade/services/ledger_reminder_service.py)
  - [services/notification_center_service.py](C:/2026/manditrade/manditrade/services/notification_center_service.py)
  - [services/action_center_service.py](C:/2026/manditrade/manditrade/services/action_center_service.py)
  - [services/manufacturer_onboarding_service.py](C:/2026/manditrade/manditrade/services/manufacturer_onboarding_service.py)
  - [services/security_service.py](C:/2026/manditrade/manditrade/services/security_service.py)
  - [services/oauth_callback_service.py](C:/2026/manditrade/manditrade/services/oauth_callback_service.py)
- Admin/manufacturer UI:
  - [modules/admin/dashboard.py](C:/2026/manditrade/manditrade/modules/admin/dashboard.py)
  - [modules/onboarding/manufacturer_onboarding.py](C:/2026/manditrade/manditrade/modules/onboarding/manufacturer_onboarding.py)
  - [modules/inventory/management.py](C:/2026/manditrade/manditrade/modules/inventory/management.py)
  - [modules/rfq/dashboard.py](C:/2026/manditrade/manditrade/modules/rfq/dashboard.py)
  - [modules/ledger/dashboard.py](C:/2026/manditrade/manditrade/modules/ledger/dashboard.py)
  - [modules/payments/dashboard.py](C:/2026/manditrade/manditrade/modules/payments/dashboard.py)
- Tests:
  - [tests/test_transactions.py](C:/2026/manditrade/manditrade/tests/test_transactions.py)
  - [tests/test_oauth_runtime.py](C:/2026/manditrade/manditrade/tests/test_oauth_runtime.py)
  - [tests/test_manufacturer_onboarding.py](C:/2026/manditrade/manditrade/tests/test_manufacturer_onboarding.py)

## Current Navigation Intent
Expected sidebar for admin:
- Dashboard
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
- Manufacturer Onboarding
- System Health

If deployed app does not show `Manufacturer Onboarding`, suspect deployment mismatch before suspecting local code.

## OAuth and Runtime Notes
- Google Sign-In is the intended active login path.
- OAuth stale-state reuse bug was fixed.
- Admin runtime verification is now one-time:
  - bootstrap secret from Streamlit secrets
  - first successful admin verify creates vault
  - later unlocks use vault-backed flow
- Vault file path:
  - `runtime/admin_vault.json`

## Manufacturer Onboarding Notes
- Admin can create/update/delete manufacturer registry entries.
- Admin can regenerate onboarding secret.
- Shareable onboarding packet is generated in UI.
- Packet instructs manufacturer to:
  - sign in with Google
  - share manufacturer code
  - share first-time onboarding secret with admin
  - get account mapped and approved

## Validation Status
- Last known local validation:
  - `python -m pytest tests/` -> `26 passed, 5 skipped`
  - `python -c "import app; print('app import ok')"` -> success

## Known Open Risk
- Deployed Streamlit app may lag latest commit even when local repo is correct.
- Build marker in sidebar should now help detect deployment mismatch instantly.

## What A Checker LLM Should Do Next
1. Confirm deployed UI matches local navigation and build marker.
2. Review admin manufacturer onboarding flow end-to-end in UI.
3. Verify role handling for `platform_admin`, `manufacturer`, `client`, and any remaining `admin` compatibility paths.
4. Review old agreement-era files for dead code still on disk but not wired.
5. Validate whether `admin_as_manufacturer` needs explicit UI/session mapping beyond current service-level support.
