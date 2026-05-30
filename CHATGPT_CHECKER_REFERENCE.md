# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the public marketplace + instant-pay flow pass.

## Current High-Signal Updates

- Public marketplace flow is now active alongside the existing private-client proposal flow.
- Business split is now explicit:
  - `PUBLIC_BUYER` = instant-pay marketplace
  - `CLIENT` = proposal + manufacturer confirmation + khata
  - `MANUFACTURER / ADMIN_AS_MANUFACTURER` = private workspace + seller fulfilment
  - `PLATFORM_ADMIN` = governance + public-order monitoring
- Public buyers can browse only `ACTIVE` + `PUBLIC` + `available_for_public_sale = true` products.
- Public checkout uses manual upfront payment only:
  - order created
  - UTR / payment reference submitted
  - seller/admin verifies payment
  - self inventory reserved
  - seller confirms
  - seller dispatches
  - buyer confirms delivery
- Private client order flow remains proposal-based and unchanged in business logic.

## Public Marketplace Status

### New Services

- [services/public_buyer_service.py](C:/2026/manditrade/manditrade/services/public_buyer_service.py)
- [services/public_cart_service.py](C:/2026/manditrade/manditrade/services/public_cart_service.py)
- [services/public_order_service.py](C:/2026/manditrade/manditrade/services/public_order_service.py)

### New Pages

- [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)
- [modules/public_orders/dashboard.py](C:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)

### Route / Navigation Wiring

- [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
- [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py)

### Marketplace Rules

Public marketplace shows only products where:

- `status = ACTIVE`
- `approved_visibility = PUBLIC`
- `available_for_public_sale = true`
- `visible = true`

Public buyers can see:

- product name
- description
- category
- unit
- approved MRP / MRP
- minimum order quantity

Public buyers do not see:

- `mandi_price`
- `suggested_mandi_price`
- `approved_mandi_price`
- proposal comments
- admin note
- inventory buckets
- RFQ data
- ledger data
- internal seller notes

## Public Instant-Pay Order Status

### Public Cart

Active in [services/public_cart_service.py](C:/2026/manditrade/manditrade/services/public_cart_service.py)

Current rules:

- cart totals are calculated from MRP only
- cart is seller-bound
- multi-seller checkout is blocked in the current MVP
- cart status stays `OPEN`

### Public Order

Active in [services/public_order_service.py](C:/2026/manditrade/manditrade/services/public_order_service.py)

Implemented statuses in the active flow:

- `PAYMENT_PENDING`
- `PAID`
- `CONFIRMED`
- `DISPATCHED`
- `DELIVERED`

Supporting fields include:

- `payment_mode = UPI_MANUAL`
- `payment_status`
- `payment_reference`
- `payment_screenshot_placeholder`
- `assigned_seller_manufacturer_id`
- `inventory_reserved`

### Payment Flow

Current public payment behavior:

- full upfront payment required
- buyer submits UTR / payment reference
- optional screenshot placeholder field exists
- seller/admin verifies payment
- no public ledger entry is created by default
- Gmail uses the existing runtime trigger model, not a queue UI

## Private Client Proposal Flow Preserved

Private client flow is still active and unchanged in its core business model:

- client places multi-product proposal
- payment proposal is allowed
- manufacturer confirms / counters
- ledger / khata can be created

Relevant services remain:

- [services/order_transaction_service.py](C:/2026/manditrade/manditrade/services/order_transaction_service.py)
- [services/ledger_service.py](C:/2026/manditrade/manditrade/services/ledger_service.py)

## RBAC / Privacy Guarantees

### Public Buyer

Navigation:

- `Marketplace`
- `My Orders`
- `My Actions`
- `Notifications`
- `My Profile`

Public buyer does not get navigation access to:

- `Inventory`
- `Client Orders`
- `Mandi RFQ`
- `Ledger / Khata`
- `Product Approvals`
- `Manufacturers`
- `System Health`

### Manufacturer / Admin-as-Manufacturer

New public-facing additions:

- `Marketplace Preview`
- `Public Orders`

Private manufacturer workspace remains intact.

### Platform Admin

New public-facing additions:

- `Marketplace`
- `Public Orders`

Admin still retains:

- `Products`
- `Product Approvals`
- `Manufacturers`
- `System Health`

## Inventory Rule Status

Public order fulfilment uses seller `self_inventory`, not `mandi_inventory`.

Implemented behavior:

- payment verification reserves seller self inventory
- delivery finalizes reserved self inventory
- mandi inventory is not auto-consumed for public orders

Relevant file:

- [services/dual_inventory_service.py](C:/2026/manditrade/manditrade/services/dual_inventory_service.py)

## Notification / Gmail Status

### In-App Notifications Added For Public Flow

- `PUBLIC_ORDER_CREATED`
- `PUBLIC_PAYMENT_SUBMITTED`
- `PUBLIC_PAYMENT_VERIFIED`
- `PUBLIC_ORDER_CONFIRMED`
- `PUBLIC_ORDER_DISPATCHED`
- `PUBLIC_ORDER_DELIVERED`

### Public Buyer Notifications

Public buyer notifications now use extended notification-center support:

- [services/notification_center_service.py](C:/2026/manditrade/manditrade/services/notification_center_service.py)

### Gmail Runtime

Still runtime-triggered only.

No queue UI was reintroduced.

## My Actions Status

Public marketplace actions are now included in [services/action_center_service.py](C:/2026/manditrade/manditrade/services/action_center_service.py).

### Public Buyer

- `COMPLETE_PUBLIC_PAYMENT`
- `UPLOAD_PAYMENT_REFERENCE`
- `CONFIRM_PUBLIC_DELIVERY`

### Seller / Manufacturer

- `VERIFY_PUBLIC_PAYMENT`
- `CONFIRM_PUBLIC_ORDER`
- `DISPATCH_PUBLIC_ORDER`

### Platform Admin

- `MONITOR_PUBLIC_ORDERS`
- `REVIEW_FAILED_PUBLIC_PAYMENT`

## My Profile Status

Public buyer profile support is now active in:

- [modules/profile/dashboard.py](C:/2026/manditrade/manditrade/modules/profile/dashboard.py)

Supported fields:

- full name
- mobile
- alternate mobile
- delivery address
- landmark
- delivery instructions

## Product Governance Updates Relevant To Marketplace

Public fulfilment now depends on:

- `approved_visibility`
- `available_for_public_sale`
- `public_seller_manufacturer_id`

Admin product approval/update surfaces were extended so public-seller assignment can be managed in:

- [modules/admin/product_approvals.py](C:/2026/manditrade/manditrade/modules/admin/product_approvals.py)
- [modules/products/dashboard.py](C:/2026/manditrade/manditrade/modules/products/dashboard.py)

## UI / Shell Status

The futuristic CSS-only shell remains active and was reused for the new public pages.

Relevant files:

- [assets/styles/manditrade_3d.css](C:/2026/manditrade/manditrade/assets/styles/manditrade_3d.css)
- [components/ui_shell.py](C:/2026/manditrade/manditrade/components/ui_shell.py)
- [utils/ui_shell.py](C:/2026/manditrade/manditrade/utils/ui_shell.py)

## Current Tests / Validation

### `python -m pytest tests/ -q`

```text
sssss................................................................... [ 94%]
....                                                                     [100%]
71 passed, 5 skipped in 15.50s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Files Most Relevant To This Pass

- [bootstrap/app_bootstrap.py](C:/2026/manditrade/manditrade/bootstrap/app_bootstrap.py)
- [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py)
- [bootstrap/service_container.py](C:/2026/manditrade/manditrade/bootstrap/service_container.py)
- [services/access_portal_service.py](C:/2026/manditrade/manditrade/services/access_portal_service.py)
- [services/action_center_service.py](C:/2026/manditrade/manditrade/services/action_center_service.py)
- [services/auth_service.py](C:/2026/manditrade/manditrade/services/auth_service.py)
- [services/notification_center_service.py](C:/2026/manditrade/manditrade/services/notification_center_service.py)
- [services/product_catalog_service.py](C:/2026/manditrade/manditrade/services/product_catalog_service.py)
- [services/public_buyer_service.py](C:/2026/manditrade/manditrade/services/public_buyer_service.py)
- [services/public_cart_service.py](C:/2026/manditrade/manditrade/services/public_cart_service.py)
- [services/public_order_service.py](C:/2026/manditrade/manditrade/services/public_order_service.py)
- [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py)
- [modules/public_orders/dashboard.py](C:/2026/manditrade/manditrade/modules/public_orders/dashboard.py)
- [modules/notifications/dashboard.py](C:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- [modules/profile/dashboard.py](C:/2026/manditrade/manditrade/modules/profile/dashboard.py)
- [tests/test_public_marketplace.py](C:/2026/manditrade/manditrade/tests/test_public_marketplace.py)
- [tests/test_access_portal.py](C:/2026/manditrade/manditrade/tests/test_access_portal.py)

## Remaining Blockers

1. Public buyer registration is currently Google-sign-in-first for actual checkout; open anonymous checkout was not added in this pass.
2. Multi-seller public carts are blocked rather than split into seller-wise orders.
3. Public payment verification is manual UTR verification only; no Razorpay / automated gateway integration exists.
4. `admin_as_manufacturer` role UX is still not a polished active switch flow, even though seller/public-order support accepts the role shape.
5. Legacy agreement-era files still remain in the repository even though public/private/marketplace flows do not rely on them.

## Acceptance Snapshot

- public buyers can browse public active products: `DONE`
- public buyer cart exists: `DONE`
- public orders require upfront payment: `DONE`
- payment reference flow exists: `DONE`
- seller/admin payment verification exists: `DONE`
- seller confirm/dispatch flow exists: `DONE`
- public buyers cannot access RFQ / ledger / inventory nav: `DONE`
- private client proposal flow preserved: `DONE`
- tests passing: `DONE`
- app imports cleanly: `DONE`
