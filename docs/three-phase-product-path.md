## MandiTrade Three-Phase Product Path

### 1. Current E2E Workspace Snapshot

The current workspace already supports a meaningful trade facilitation flow:

- Google Drive bootstrapped JSON runtime with role-based modules
- user roles for `platform_admin`, `manufacturer`, `merchant`, `delivery_partner`, `public_buyer`, and `worker`
- product onboarding and owner-linked catalog management
- two commercial channels:
  - `marketplace` for B2C
  - `manditrade` for B2B
- owner-aware payment link generation
- order creation, notifications, shipment assignment, delivery confirmation, and owner settlement ledger

### 2. What The Current Logic Actually Does

#### Identity and access

- `platform_admin` controls the platform, bootstrap, runtime setup, and system health
- `manufacturer` and `merchant` act as business owners with their own products
- `public_buyer` places B2C marketplace orders
- `delivery_partner` handles assigned deliveries
- `worker` is currently lightweight and mostly notification-focused

#### Product and channel model

- products already carry:
  - owner
  - pricing
  - inventory
  - `sales_channels.marketplace`
  - `sales_channels.manditrade`
- B2C and B2B are already separated at channel level

#### Order and payment model

- `marketplace` orders are created as B2C
- `manditrade` orders are created as B2B
- payment records are generated with owner-specific UPI receiver configuration
- payment collection is owner-facing, while the platform monitors status

#### Shipment model

- owner marks orders ready for pickup
- owner assigns delivery partner
- delivery partner confirms pickup, moves shipment to in-transit, and verifies delivery with OTP

#### Ledger model

- ledger currently focuses mainly on:
  - payable to owner
  - payment to owner
- this is enough for simple owner settlement
- this is not yet enough for a multi-service model with platform margin, packaging revenue, shipping revenue, and service settlement splits

### 3. Core Product Direction

The target business is not a basic marketplace. It is a trade facilitation operating system where:

- offline businessmen are onboarded into digital selling
- they retain ownership of their products and customers
- MandiTrade provides digital distribution
- MandiTrade may also provide packaging and shipping as separate services
- every commercial and fulfillment event should produce runtime ledger impact

This creates three business layers:

- commerce enablement
- packaging service
- shipping/logistics service

### 4. UX Direction By User Type

#### Platform admin

Needs:

- operational visibility
- onboarding control
- commercial configuration
- ledger and settlement oversight
- service health and exception monitoring

Best experience:

- command-center dashboard
- onboarding approval queue
- owner settlement console
- packaging and shipping service revenue console
- business KPIs split by channel and service type

#### Manufacturer / Merchant

Needs:

- easy onboarding
- product upload and catalog management
- B2C/B2B pricing control
- optional packaging and shipping configuration
- order management
- payout and ledger clarity

Best experience:

- owner workspace
- guided product onboarding
- clear per-product commercial breakdown
- order pipeline by status
- settlement and service deduction visibility

#### Public buyer

Needs:

- trust
- clean product browsing
- simple checkout
- payment clarity
- delivery tracking

Best experience:

- marketplace-first UX
- product trust badges
- simple B2C checkout
- payment confirmation guidance
- order and tracking timeline

#### Delivery partner

Needs:

- simple queue
- pickup clarity
- route-ready shipment detail
- OTP delivery confirmation

Best experience:

- mobile-friendly task list
- status-driven shipment actions
- proof-of-delivery flow

### 5. Three Phases To Completion

## Phase 1: Stabilize The Trade Facilitation Core

Goal:

- make the current B2B/B2C facilitator model clean, consistent, and trustworthy

Scope:

- standardize role catalog, permissions, navigation, and labels
- tighten businessman onboarding flow for `manufacturer` and `merchant`
- make product onboarding owner-first with:
  - owner identity
  - B2C enablement
  - B2B enablement
  - pricing by channel
  - inventory
  - preferred delivery setup
- improve dashboards by role with cleaner decision-focused metrics
- ensure all tables and high-traffic pages use the refined template-driven UI
- make orders, products, payments, and shipments feel like guided workflows instead of raw admin pages

Success outcome:

- the platform becomes a reliable digital extension of the businessman's offline business

Key implementation targets:

- `modules/products.py`
- `modules/orders.py`
- `modules/shipments.py`
- `modules/payments.py`
- `components/page_renderer.py`
- role/config files in `bootstrap_seed/live/00_config`

## Phase 2: Add Service Economics For Packaging And Shipping

Goal:

- make fulfillment a first-class business line, not just an operational afterthought

Scope:

- add product onboarding fields for:
  - packaging mode
  - shipping mode
  - packaging charges by channel
  - shipping charges by channel
  - service ownership: owner-managed vs MandiTrade-managed
- support hybrid fulfillment responsibility
- generate order-level commercial splits for:
  - owner base amount
  - platform margin
  - packaging charge
  - shipping charge
  - delivery partner payable
- expose this clearly to owners and admin
- introduce operational UX for fulfillment choice and cost traceability

Success outcome:

- MandiTrade becomes a revenue-generating fulfillment facilitator, not only a seller-side marketplace

Key implementation targets:

- `modules/products.py`
- `services/order_service.py`
- `services/payment_service.py`
- `modules/shipments.py`
- seed config/data models in `bootstrap_seed`

## Phase 3: Build Multi-Party Runtime Ledger And Settlement OS

Goal:

- make the platform financially authoritative across commerce and services

Scope:

- redesign ledger from simple owner payable tracking to multi-party runtime accounting
- support entries for:
  - product sale
  - B2C margin
  - B2B margin
  - packaging fee
  - shipping fee
  - owner payable
  - delivery partner payable
  - settlement payout
  - adjustments and refunds
- create settlement dashboards by stakeholder
- give admin visibility into:
  - outstanding payables
  - revenue by channel
  - revenue by service type
  - pending settlements
  - exception cases
- provide owner-facing earnings and deduction trace

Success outcome:

- MandiTrade becomes a complete trade operations and settlement engine

Key implementation targets:

- `services/ledger_service.py`
- `services/order_service.py`
- `modules/ledger.py`
- `modules/payments.py`
- `services/integration_status_service.py`

### 6. Recommended Execution Order

1. finish Phase 1 first
2. add fulfillment service economics in Phase 2
3. only then redesign ledger for full financial truth in Phase 3

This order matters because:

- Phase 1 stabilizes user workflows
- Phase 2 stabilizes business model inputs
- Phase 3 stabilizes financial outputs

### 7. Product Principle For Every Phase

Every change should preserve one core rule:

`The businessman owns the trade. MandiTrade digitizes, facilitates, services, and settles it cleanly.`

