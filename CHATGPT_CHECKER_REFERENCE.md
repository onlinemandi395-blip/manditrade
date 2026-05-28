# MandiTrade Current-State Audit

Generated from the current repository code and config only. Old markdown was not used as source-of-truth.

## 1. Latest Code Changes

- Google Sign-In only flow: `modules/access/dashboard.py` now renders a pure Google login page. `bootstrap/app_bootstrap.py` sends unauthenticated users to this page and routes OAuth callback results through `services/access_portal_service.py`.
- Mock login removal status: `configs/system_config.json` sets `enable_mock_auth=false` and `enable_dev_mock_login=false`. No mock login UI is routed. Mock helpers still exist in `services/auth_service.py` and `services/oauth_callback_service.py`.
- Cloud/staging configuration: `configs/system_config.json` is set to `runtime_environment=staging_cloud`, `staging_mode=true`, `safe_mode=true`, `notification_mode=live`, `use_drive_api=true`, `use_gmail_api=true`.
- Product model: `services/product_catalog_service.py` implements proposal + approval with `product_id`, `mandi_price`, `mrp`, `status`, `created_by`, `approved_by`.
- Dual inventory: `services/dual_inventory_service.py` implements `self_inventory`, `mandi_inventory`, reserve, release, finalize, self->mandi transfer, and mandi->self withdraw.
- RFQ flow: `services/procurement_transaction_service.py` creates shortage RFQs, stores responses, and creates trade confirmations plus ledger entries on acceptance.
- Ledger/khata: `services/ledger_service.py` creates bilateral ledgers and supports payment posting.
- Payment proposal: `services/order_transaction_service.py` stores `payment_proposal` on order creation and uses it during confirmation to create ledger entries.
- Gmail reminders: `services/ledger_reminder_service.py` implements `UPCOMING_DUE`, `DUE_TODAY`, `OVERDUE`, and `FINAL_REMINDER` using the Gmail queue.
- In-app notifications: `services/notification_center_service.py` creates notifications for RFQ creation, RFQ acceptance, and job updates.
- My Actions tab: `services/action_center_service.py` computes role-based action items; `modules/actions/dashboard.py` renders them.
- Agreement removal/replacement status: active order/RFQ flow uses `services/trade_confirmation_service.py`. Legacy agreement files still exist on disk and are not fully removed.

## 2. Current Active Business Logic

### Admin / Owner
- Login is Google-only.
- If signed-in email matches `[admin].admin_email`, `services/access_portal_service.py::resolve_identity` returns `platform_admin`.
- Active admin pages: product approval, manufacturer onboarding, system health, notifications, products.
- Admin runtime unlock is separate and handled by `services/security_service.py`.

### Admin-as-Manufacturer
- PARTIAL.
- `admin_as_manufacturer` is accepted by routing and some dashboards, but no active identity resolver or switch UI creates this role.
- Current code supports the role shape, but not the session acquisition flow.

### Manufacturer
- Resolved by matching Google email to `owner_email` in governance manufacturers.
- Can propose products, manage dual inventory, see orders, RFQs, ledgers, clients, jobs, workers.
- Order confirmation, dispatch, and delivery exist in services, but main routed dashboards are mostly read/report views, not full action forms.

### Client
- Resolved by matching Google email to an activated client profile or validated invite.
- Client dashboard is active.
- Client order placement is implemented in service code, but the current routed `Client Orders` page uses manufacturer-wide order listing, not client-filtered listing.
- Client ledger and notification views are also not client-filtered.

### Product Onboarding
- Implemented.
- Product proposal happens through `services/product_catalog_service.py::propose_product`.
- Manufacturer and platform admin can submit proposals from `modules/products/dashboard.py`.

### Product Approval
- Implemented.
- Platform admin approves from `modules/admin/dashboard.py`.
- Approval sets `mandi_price`, `mrp`, `status=ACTIVE`, `approved_by`, `approved_at`.

### Client Multi-Product Order
- Implemented at service level.
- `services/order_transaction_service.py::create_order` accepts `items: list[dict]` and `payment_proposal: dict`.
- Tested in `tests/test_transactions.py`.
- Active client-facing routed placement UI is NOT IMPLEMENTED correctly in main navigation.

### Manufacturer Confirmation
- Implemented at service level.
- `services/order_transaction_service.py::confirm_order` creates a trade confirmation and a ledger entry.
- No dedicated routed confirmation UI button is present in the main dashboards.

### Mandi RFQ
- Implemented at service level.
- If self inventory is short during order creation, `create_order` auto-creates RFQ via `create_rfq_from_shortage`.
- RFQ dashboard currently displays data; active create/respond forms are not present in the main routed RFQ page.

### RFQ Response
- Implemented at service level.
- `respond_to_rfq` reserves supplier mandi inventory and records a response.
- `accept_rfq_response` confirms buyer acceptance, creates trade confirmation, and creates ledger entry.
- Full RFQ lifecycle states from the product spec are NOT IMPLEMENTED.

### Payment Proposal
- Implemented at service level.
- Stored on order as `payment_proposal`.
- Used during order confirmation to compute `paid_amount`, `ledger_days`, and ledger note.
- Dedicated negotiation/counter-proposal UI is NOT IMPLEMENTED.

### Udhar / Ledger
- Implemented.
- Ledger entries are created on order confirmation and RFQ acceptance.
- Manual `add_payment` exists.
- Return/damage note support is NOT IMPLEMENTED as a dedicated field/flow.

### Payment Reminder
- Implemented.
- `LedgerReminderService.run_for_manufacturer()` classifies due items and enqueues Gmail reminders with duplicate prevention.

### In-App Notification
- Implemented.
- Notification service supports create/list/update.
- UI currently lists notifications, but explicit mark-read/resolve/remind-later controls are NOT IMPLEMENTED in the routed page.

### My Actions
- Implemented as computed data, not persisted records.
- Admin: manufacturer approvals, product approvals, failed Gmail queue.
- Manufacturer: confirm order, respond RFQ, dispatch pending, overdue payment, low inventory, review worker application.
- Client: accept counter proposal, confirm delivery, worker response prompt.
- Worker: respond to job, confirm attendance.

## 3. Current Data Model

### Product Catalog
```json
{
  "product_id": "PRD-2026-000001",
  "name": "Rice",
  "category": "Grain",
  "unit": "kg",
  "mandi_price": 40.0,
  "mrp": 50.0,
  "status": "ACTIVE",
  "created_by": "MANU101",
  "approved_by": "PLATFORM_ADMIN",
  "created_at": "",
  "approved_at": ""
}
```

### Manufacturer Profile
```json
{
  "manufacturer_code": "MANU101",
  "manufacturer_name": "Shree Agro Traders",
  "owner_email": "owner@example.com",
  "city": "Pune",
  "status": "pending_approval",
  "subscription_plan": "basic",
  "manufacturer_onboarding_secret": "MANU-SETUP-...",
  "workspace_root": "",
  "shared_zone": "",
  "private_zone": "",
  "created_by": "",
  "created_at": "",
  "manufacturer_onboarding_steps": ""
}
```

### Client Profile
```json
{
  "client_id": "CLIENT101",
  "manufacturer_id": "MANU101",
  "business_name": "Kumar Traders",
  "owner_name": "Amit Kumar",
  "email": "buyer@example.com",
  "city": "Pune",
  "credit_limit": 50000,
  "status": "ACTIVE",
  "updated_at": ""
}
```

### Self + Mandi Inventory Record
```json
{
  "manufacturer_id": "MANU101",
  "product_id": "PRD-2026-000001",
  "product_name": "Rice",
  "self_inventory": {
    "available_qty": 500,
    "reserved_qty": 0,
    "unit": "kg"
  },
  "mandi_inventory": {
    "available_qty": 200,
    "reserved_qty": 0,
    "unit": "kg",
    "visible_to_mandi": true
  }
}
```

### Client Order
```json
{
  "schema_version": "2.0",
  "order_id": "ORD-2026-000001",
  "client_id": "CLIENT101",
  "client_email": "buyer@example.com",
  "manufacturer_id": "MANU101",
  "primary_manufacturer_id": "MANU101",
  "items": [],
  "payment_proposal": {
    "payment_modes": ["cash", "upi"],
    "upfront_percentage": 30,
    "ledger_days": 10,
    "freestyle_note": "30% upfront online"
  },
  "status": "PROPOSED",
  "created_at": "",
  "created_at_runtime": "",
  "status_history": [],
  "transaction_id": "TXN-2026-000001",
  "rfq_id": "",
  "trade_confirmation_id": ""
}
```

### Mandi RFQ
```json
{
  "rfq_id": "RFQ-2026-000001",
  "buyer_manufacturer_id": "MANU101",
  "items": [],
  "trade_terms": {},
  "status": "OPEN",
  "created_at": ""
}
```

### RFQ Response
```json
{
  "response_id": "RESP-2026-000001",
  "supplier_manufacturer_id": "MANU202",
  "rfq_id": "RFQ-2026-000001",
  "available_items": [],
  "supplier_terms": {},
  "status": "SUBMITTED",
  "created_at": ""
}
```

### Trade Confirmation
```json
{
  "confirmation_id": "TC-2026-000001",
  "source_type": "CLIENT_ORDER",
  "source_id": "ORD-2026-000001",
  "confirmed_by": "owner@example.com",
  "accepted_terms_snapshot": {},
  "confirmed_at": ""
}
```

### Ledger Entry
```json
{
  "entry_id": "LEDENT-2026-000001",
  "entry_type": "ORDER_SUPPLIED",
  "amount": 1000.0,
  "paid_amount": 400.0,
  "balance_due": 600.0,
  "due_date": "2026-06-05",
  "note": "40% paid",
  "status": "PENDING",
  "created_at": "",
  "reminders_sent": [],
  "adjustment_note": ""
}
```

### Notification
```json
{
  "notification_id": "NOTIF-2026-000001",
  "user_id": "MANU101",
  "type": "RFQ_ACCEPTED",
  "priority": "HIGH",
  "title": "RFQ Accepted",
  "message": "A supplier accepted your mandi RFQ.",
  "source_type": "RFQ",
  "source_id": "RFQ-2026-000001",
  "read": false,
  "resolved": false,
  "remind_later_at": "",
  "created_at": ""
}
```

### Action Item
Computed only. No JSON file.
```json
{
  "type": "APPROVE_PRODUCT",
  "count": 3
}
```

## 4. Public vs Private Data Classification

### Platform / Public Data
- `data/governance/products.json`
- Current products dashboard exposes all products, including pending products

### Manufacturer Private Data
- `private_zone/clients.json`
- `private_zone/client_profiles/*.json`
- `private_zone/client_orders/*.json`
- `private_zone/ledgers.json`
- `private_zone/notifications.json`
- `private_zone/api_keys.json`
- `private_zone/manufacturer_config.json`

### Mandi-Shared Data
- `shared_zone/rfqs.json`
- `shared_zone/trade_confirmations.json`
- `shared_zone/orders/*`
- `shared_zone/inventory.json`

### Client-Private Data
- Client profile files in `private_zone/client_profiles/*.json`
- Invite tokens stored in manufacturer-private `clients.json`

### Admin-Platform Data
- `data/governance/manufacturers.json`
- `data/governance/products.json`
- `data/governance/access_requests.json`
- health dashboard / runtime reports

### Admin-as-Manufacturer Data
- Intended to be same as manufacturer data
- Current session acquisition is NOT IMPLEMENTED

### Important Current Mismatch
- `shared_zone/inventory.json` contains both `self_inventory` and `mandi_inventory`.
- `shared_zone/orders/*` stores full order documents even though a private copy is also written.
- This means current storage layout does not fully enforce the intended public/private split.

## 5. Removed / Deprecated Features

- Agreement PDFs: FULLY REMOVED from active path. No active PDF generation code found.
- Agreement lifecycle: PARTIAL. Legacy files still exist: `modules/agreements/dashboard.py`, `services/query/agreement_query_service.py`, `schemas/agreement_schema.json`, `services/id_allocator_service.py` (`agreement` prefix).
- Agreement settlement engine: PARTIAL. `services/agreement_settlement_service.py` still exists but is not wired into active routes/services.
- Mock login: PARTIAL. Disabled by config and not exposed in UI, but `AuthService.create_mock_user()` and mock session branch in `OAuthCallbackService.initialize_session()` still exist.
- Demo login: FULLY REMOVED from visible UI.
- Fake runtime behavior: PARTIAL. `effective_demo_mode` still exists and can disable live Google runtime when blockers are present.
- Old transaction types if no longer needed: PARTIAL. `agreement` ID prefix still exists in `services/id_allocator_service.py`.

## 6. Runtime Configuration

### `configs/system_config.json`
- `runtime_environment`: `staging_cloud`
- `notification_mode`: `live`
- `demo_mode`: `false`
- `staging_mode`: `true`
- `safe_mode`: `true`
- `use_drive_api`: `true`
- `use_gmail_api`: `true`
- `enable_mock_auth`: `false`
- `enable_dev_mock_login`: `false`

### `configs/oauth_config.json`
- `redirect_uri`: `http://localhost:8501`
- `client_id`: empty
- `client_secret`: empty
- `allow_secret_override`: `true`

### `.streamlit/secrets.toml.template`
- `[google].redirect_uri`: `https://YOUR-APP-NAME.streamlit.app`
- `[admin].admin_email`: `admin@manditrade.in`
- `[security].public_verification_key`: placeholder
- `[security].fernet_key`: placeholder
- `[admin_token].encrypted_token`: empty

### Redirect URI Source
- Current runtime source precedence is:
  1. `.streamlit` secrets `[google].redirect_uri` if present
  2. otherwise `configs/oauth_config.json`
- This is implemented in `bootstrap/service_container.py`.

## 7. Current Cloud Readiness

Target:
`https://manpur-mandi-trade.streamlit.app`

- Google OAuth readiness: PARTIAL.
  - Code path is ready.
  - Repo defaults are not ready: `oauth_config.json` uses localhost and empty client values.
  - Runtime depends on Streamlit secrets override and matching Google Cloud redirect URI.

- Drive runtime readiness: PARTIAL.
  - `use_drive_api=true` and diagnostics exist.
  - Real readiness depends on valid OAuth secrets and token refresh at runtime.

- Gmail runtime readiness: PARTIAL.
  - `notification_mode=live` and `use_gmail_api=true`.
  - Real send readiness depends on valid OAuth secrets and token refresh at runtime.

- Admin token readiness: PARTIAL.
  - `configs/admin_token.enc` exists and is non-placeholder.
  - `runtime/admin_vault.json` does not exist in repo.
  - Actual decrypt/refresh readiness is secrets-dependent and was not proven by this audit.

- Remaining redirect URI issues:
  - `configs/oauth_config.json` still points to `http://localhost:8501`
  - `.streamlit/secrets.toml.template` is still generic and not set to `https://manpur-mandi-trade.streamlit.app`

- Secrets dependency:
  - Required sections: `[security]`, `[google]`, `[admin]`
  - Required fields are enforced by `ConfigService.validate_streamlit_secrets()`

- Deployment blockers from current repo state alone:
  - No repo-level OAuth client values
  - Repo-level redirect URI is localhost
  - Streamlit secrets template is placeholder-based, not deployment-ready

## 8. Exact Remaining Blockers

### Blocker 1
- file: `services/access_portal_service.py`
- function/class: `AccessPortalService.resolve_identity`
- problem: `admin_as_manufacturer` is never resolved; role exists in UI/service checks but has no active acquisition flow.
- recommended fix: add explicit admin-to-manufacturer context switch and set `admin_as_manufacturer` in session.
- priority: HIGH

### Blocker 2
- file: `modules/orders/dashboard.py`
- function/class: `render_orders_dashboard`
- problem: page lists all manufacturer orders for any user with `manufacturer_code`, including clients.
- recommended fix: branch by role and use `order_query_service.list_orders_for_client()` for clients.
- priority: HIGH

### Blocker 3
- file: `modules/ledger/dashboard.py`
- function/class: `render_ledger_dashboard`
- problem: page lists all manufacturer ledgers for any user with `manufacturer_code`, including clients.
- recommended fix: add per-party filtering before rendering client ledger view.
- priority: HIGH

### Blocker 4
- file: `modules/notifications/dashboard.py`
- function/class: `render_notifications_dashboard`
- problem: full Gmail queue is displayed to every signed-in user; notifications are only manufacturer-scoped, not user-scoped.
- recommended fix: restrict Gmail queue to platform admin/manufacturer admins and filter in-app notifications by `user_id`.
- priority: HIGH

### Blocker 5
- file: `services/domain_paths_service.py`
- function/class: `inventory_path`, `orders_month_dir`
- problem: `self_inventory` and full order documents live in shared-zone storage, which conflicts with the intended privacy model.
- recommended fix: move private-only inventory/order data to private-zone paths and expose only shared mandi-safe projections in shared-zone files.
- priority: HIGH

### Blocker 6
- file: `services/procurement_transaction_service.py`
- function/class: `accept_rfq_response`
- problem: ledger amount is computed from `available_items[*].unit_price/price`, but response creation does not populate those fields; result can be `0.0`.
- recommended fix: add explicit RFQ response pricing fields and validate them before ledger creation.
- priority: HIGH

### Blocker 7
- file: `modules/products/dashboard.py`
- function/class: `render_products_dashboard`
- problem: pending products are shown to all viewers because `include_pending=True` is used before role filtering.
- recommended fix: restrict pending product visibility to platform admin/manufacturer roles or filter active-only for client/public users.
- priority: MEDIUM

### Blocker 8
- file: `services/agreement_settlement_service.py`, `modules/agreements/dashboard.py`, `services/query/agreement_query_service.py`
- function/class: `AgreementSettlementService`, `render_agreements_dashboard`, `AgreementQueryService`
- problem: agreement-era code still remains in repo and can confuse maintenance and audits.
- recommended fix: remove unused agreement modules/services/schema/query code or mark them explicitly deprecated and unreachable.
- priority: MEDIUM

### Blocker 9
- file: `configs/oauth_config.json`, `.streamlit/secrets.toml.template`
- function/class: configuration
- problem: repository defaults are not deployment-ready for `https://manpur-mandi-trade.streamlit.app`.
- recommended fix: set Streamlit secrets in deployment to real client values and exact redirect URI, and mirror that redirect in Google Cloud Console.
- priority: HIGH

## 9. Tests / Validation

### `python -m pytest tests/ -q`
```text
sssss................................                                    [100%]
32 passed, 5 skipped in 5.86s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`
```text
Listing 'modules'...
Listing 'modules\\access'...
Listing 'modules\\actions'...
Listing 'modules\\admin'...
Listing 'modules\\agreements'...
Listing 'modules\\analytics'...
Listing 'modules\\client'...
Listing 'modules\\clients'...
Listing 'modules\\inventory'...
Listing 'modules\\jobs'...
Listing 'modules\\ledger'...
Listing 'modules\\manufacturer'...
Listing 'modules\\notifications'...
Listing 'modules\\onboarding'...
Listing 'modules\\orders'...
Listing 'modules\\payments'...
Listing 'modules\\pricing'...
Listing 'modules\\procurement'...
Listing 'modules\\products'...
Listing 'modules\\rfq'...
Listing 'modules\\system'...
Listing 'modules\\workers'...
Listing 'services'...
Listing 'services\\query'...
Listing 'services\\storage'...
Listing 'utils'...
Listing 'components'...
Listing 'schemas'...
Listing 'schemas\\events'...
Listing 'bootstrap'...
Listing 'scripts'...
```

### `python -c "import app; print('app import ok')"`
```text
app import ok
2026-05-28 10:29:49.858 WARNING streamlit.runtime.caching.cache_data_api: No runtime found, using MemoryCacheStorageManager
2026-05-28 10:29:49.862 WARNING streamlit.runtime.caching.cache_data_api: No runtime found, using MemoryCacheStorageManager
2026-05-28 10:29:50.111 WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext! This warning can be ignored when running in bare mode.
```

## 10. Final Summary

Current Status:
Current codebase has active Google Sign-In-only access, product governance, dual inventory, service-level multi-product orders, RFQ creation/response, trade confirmations, ledger reminders, notifications, My Actions, and jobs/workers modules. RBAC is present, but client/private data filtering and admin-as-manufacturer activation are incomplete. Agreement-era code is not active in routing, but it is not fully removed from the repository.

Top 5 Remaining Tasks:
1. Implement a real `admin_as_manufacturer` session switch.
2. Fix client-specific filtering for orders, ledger, and notifications pages.
3. Separate private-only inventory/order data from shared-zone storage.
4. Add pricing fields to RFQ responses before ledger creation.
5. Remove or explicitly deprecate remaining agreement-era modules/services.

Recommended Next Codex Prompt:
`Audit and fix all RBAC leakage paths in the current MandiTrade codebase. Focus only on client/private visibility, admin-as-manufacturer activation, shared-zone vs private-zone storage separation, and RFQ response pricing. Update tests first for each bug, implement the fixes, run pytest/compile/import checks, and rewrite CHATGPT_CHECKER_REFERENCE.md only if the fixes change the reported status.`
