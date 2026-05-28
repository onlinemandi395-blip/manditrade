# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-28 after the manufacturer-form, product-proposal, and proposal-comment-thread cleanup pass.

## Manufacturer Form Status

- Full manufacturer onboarding/profile form lives only on the dedicated `Onboarding` route in [modules/onboarding/manufacturer_onboarding.py](C:/2026/manditrade/manditrade/modules/onboarding/manufacturer_onboarding.py).
- Manufacturer and admin dashboards do not render the full onboarding form.
- Submit/update flow uses [services/manufacturer_onboarding_service.py](C:/2026/manditrade/manditrade/services/manufacturer_onboarding_service.py).
- Manufacturer onboarding does not create any approval-pending state.
- Submitted and updated manufacturer records remain `ACTIVE`.

### Current Manufacturer Fields

- `manufacturer_id`
- `manufacturer_code`
- `business_name`
- `manufacturer_name`
- `owner_name`
- `owner_email`
- `mobile`
- `alternate_mobile`
- `address.line1`
- `address.line2`
- `address.city`
- `address.state`
- `address.pin_code`
- `business_type`
- `product_categories`
- `legal.udyam_id`
- `legal.gstin`
- `legal.pan`
- `legal.aadhaar`
- `banking.account_holder_name`
- `banking.account_number`
- `banking.ifsc`
- `banking.upi_id`
- `google_drive_connected_status`
- `business_description`
- `status`
- `created_at`
- `updated_at`
- `created_by`
- `workspace.root`
- `workspace.shared_zone`
- `workspace.private_zone`

### Manufacturer Validation Rules

- `business_name`, `owner_name`, `owner_email`, `mobile`, `city`, `state`, and `pin_code` are required.
- mobile must be 10 digits
- PIN must be 6 digits
- GSTIN must be 15 chars if provided
- PAN must be 10 chars if provided
- Aadhaar must be 12 digits if provided
- IFSC must be 11 chars if provided

## Product Proposal Form Status

- Manufacturer proposal form is active on the `Products` route in [modules/products/dashboard.py](C:/2026/manditrade/manditrade/modules/products/dashboard.py).
- Platform admin uses a dedicated approval queue in [modules/admin/product_approvals.py](C:/2026/manditrade/manditrade/modules/admin/product_approvals.py).
- Proposal and comment-thread flow uses [services/product_catalog_service.py](C:/2026/manditrade/manditrade/services/product_catalog_service.py).

### Current Product Proposal Fields

- `name`
- `category`
- `unit`
- `description`
- `suggested_mandi_price`
- `suggested_mrp`
- `visibility_request`
- `minimum_order_qty`
- `available_for_public_sale`
- `available_for_mandi_network`
- `image_url`
- `comments`
- `clarification_status`

### Current Product Proposal Model

```json
{
  "product_id": "PRD-2026-000001",
  "name": "Rice",
  "category": "Grain",
  "unit": "kg",
  "description": "Premium rice bags",
  "suggested_mandi_price": 40.0,
  "suggested_mrp": 50.0,
  "approved_mandi_price": null,
  "approved_mrp": null,
  "visibility_request": "MANDI_NETWORK",
  "approved_visibility": null,
  "minimum_order_qty": 10,
  "available_for_public_sale": false,
  "available_for_mandi_network": true,
  "image_url": "https://example.com/rice.png",
  "status": "PROPOSED",
  "comments": [],
  "clarification_status": "NONE",
  "created_by": "MANU101",
  "created_by_manufacturer_id": "MANU101",
  "created_by_email": "owner@example.com",
  "approved_by": "",
  "admin_note": "",
  "created_at": "",
  "updated_at": "",
  "approved_at": "",
  "visible": false
}
```

## Product Proposal Comment Thread Status

- Proposal comments are active and persisted inside the product proposal object.
- Only `PLATFORM_ADMIN`, `MANUFACTURER`, and `ADMIN_AS_MANUFACTURER` roles can comment.
- Only platform admin and the proposing manufacturer can read/write proposal comments.
- Clients, public users, and unrelated manufacturers cannot see or comment on proposal threads.
- Comments are append-only. No edit path exists after submit.

### Comment Model

```json
{
  "comment_id": "COM-2026-000001",
  "author_user_id": "admin@example.com",
  "author_role": "PLATFORM_ADMIN",
  "author_email": "admin@example.com",
  "message": "Please clarify unit: kg or bag?",
  "created_at": "",
  "visibility": "INVOLVED_PARTIES",
  "read_by": ["admin@example.com"]
}
```

### Clarification Status Rules

- admin comment -> `ADMIN_QUERY`
- manufacturer reply -> `MANUFACTURER_REPLIED`
- admin resolve -> `RESOLVED`
- new proposal default -> `NONE`
- approval is blocked while status is `ADMIN_QUERY`
- rejection remains allowed

## Admin Product Approval Status

- Queue shows only products where `status == PROPOSED`.
- Admin sees:
  - proposal summary
  - suggested pricing
  - visibility request
  - comment thread
  - comment box
  - resolve button
  - approve/reject controls
- Approve path captures approved price, approved visibility, and admin note.
- Reject path captures rejection note in `admin_note`.

## Notification Integration

- Admin comment creates manufacturer in-app notification:
  - `PRODUCT_PROPOSAL_COMMENTED`
- Manufacturer reply creates platform-admin in-app notification:
  - `PRODUCT_PROPOSAL_REPLIED`
- Gmail is queued through existing queue only:
  - `product_proposal_commented`
  - `product_proposal_replied`
- No direct Gmail send is done inside product service.

## My Actions Integration

Platform admin actions now include:

- `APPROVE_PRODUCT`
- `PRODUCT_PROPOSAL_CLARIFICATION_UNRESOLVED`
- `PRODUCT_PROPOSAL_REPLY_PENDING_REVIEW`

Manufacturer actions now include:

- `PRODUCT_PROPOSAL_NEEDS_REPLY`

## RBAC / Privacy Rules

- Platform admin sees all product proposals and all proposal threads.
- Manufacturer sees:
  - active visible products
  - own proposed products
  - own proposal comments only
- Clients/public users see only active visible products.
- Comment arrays and clarification state are stripped from non-involved viewer product listings.

## Duplicate Dashboard Form Removal Status

- Full manufacturer onboarding form is not rendered inside admin or manufacturer dashboard modules.
- Dedicated onboarding route is the only full manufacturer form surface.
- Admin dashboard remains summary-only.

## Files Changed In This Pass

- [services/id_allocator_service.py](C:/2026/manditrade/manditrade/services/id_allocator_service.py)
- [services/manufacturer_onboarding_service.py](C:/2026/manditrade/manditrade/services/manufacturer_onboarding_service.py)
- [services/drive_service.py](C:/2026/manditrade/manditrade/services/drive_service.py)
- [services/product_catalog_service.py](C:/2026/manditrade/manditrade/services/product_catalog_service.py)
- [services/action_center_service.py](C:/2026/manditrade/manditrade/services/action_center_service.py)
- [bootstrap/service_container.py](C:/2026/manditrade/manditrade/bootstrap/service_container.py)
- [modules/onboarding/manufacturer_onboarding.py](C:/2026/manditrade/manditrade/modules/onboarding/manufacturer_onboarding.py)
- [modules/products/dashboard.py](C:/2026/manditrade/manditrade/modules/products/dashboard.py)
- [modules/admin/product_approvals.py](C:/2026/manditrade/manditrade/modules/admin/product_approvals.py)
- [modules/notifications/dashboard.py](C:/2026/manditrade/manditrade/modules/notifications/dashboard.py)
- [tests/helpers/fake_storage.py](C:/2026/manditrade/manditrade/tests/helpers/fake_storage.py)
- [tests/test_business_cleanup.py](C:/2026/manditrade/manditrade/tests/test_business_cleanup.py)
- [tests/test_manufacturer_onboarding.py](C:/2026/manditrade/manditrade/tests/test_manufacturer_onboarding.py)

## Test Results

### `python -m pytest tests/ -q`

```text
sssss.....................................................               [100%]
53 passed, 5 skipped in 8.94s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blocker

Main remaining blockers after this pass:

1. `admin_as_manufacturer` role shape exists but active session-switch flow is still partial.
2. Broader client/private filtering outside product catalog still needs a dedicated audit on orders, ledger, and some notification surfaces.
3. Shared-zone vs private-zone storage separation for inventory/orders remains incomplete.
4. RFQ response pricing validation still needs a separate fix pass.
5. Agreement-era legacy files still exist in the repository even though they are not on the active workflow path.

## Current Acceptance Check

- product proposal supports comment thread: `DONE`
- platform admin and proposing manufacturer can chat over proposal: `DONE`
- comments are hidden from clients/public/unrelated manufacturers: `DONE`
- notifications are generated for comment/reply: `DONE`
- My Actions reflects pending replies/reviews: `DONE`
- approval queue displays comments: `DONE`
- manufacturer proposal page displays comments/reply option: `DONE`
- tests pass: `DONE`
- app imports cleanly: `DONE`
