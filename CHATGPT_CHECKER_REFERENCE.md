# MandiTrade Checker Reference

Generated from the current repository state after the manufacturer onboarding, product approval, and navigation cleanup pass.

## Current Status

- Manufacturer onboarding no longer uses approval-pending states.
- New manufacturer registry records are created with `status = ACTIVE`.
- Manufacturer first-login activation keeps manufacturer status `ACTIVE`; no platform approval action is required.
- Product proposals now use `status = PROPOSED`.
- Platform Admin approves products through a separate `Product Approvals` page.
- Only `ACTIVE` and visible products are returned to clients/public viewers.
- Dashboard no longer contains duplicate manufacturer onboarding forms.
- Onboarding remains a separate navigation page.

## Manufacturer Onboarding Behavior

Business rule now implemented:

```text
Manufacturer onboarding does not require approval.
```

Actual behavior:

1. Platform Admin creates manufacturer onboarding packet.
2. Manufacturer registry record is saved with `status = ACTIVE`.
3. Manufacturer signs in with Google and validates onboarding packet.
4. Access activation keeps manufacturer status `ACTIVE`.
5. Manufacturer can use the dashboard without any admin approval queue.

Status normalization:

- Removed active usage of:
  - `pending_approval`
  - `approval_pending`
- Manufacturer lifecycle now uses:
  - `ACTIVE`
  - `INACTIVE`
  - `BLOCKED`

Admin action changes:

- Removed `APPROVE_MANUFACTURER` from admin action aggregation.
- Admin can still view manufacturers and change lifecycle state, but not approve onboarding.

## Product Approval Flow

Business rule now implemented:

```text
Manufacturer proposes product
Platform Admin approves product
Only ACTIVE products are visible to clients/public users
```

Current product states:

- `PROPOSED`
- `ACTIVE`
- `REJECTED`

Implemented behavior:

- Manufacturer/admin proposal creates:

```json
{
  "status": "PROPOSED",
  "created_by": "MANUFACTURER_ID",
  "visible": false
}
```

- Platform Admin approval captures:
  - `mandi_price`
  - `mrp`
  - `category`
  - `unit`
  - `visible`

- Approval updates product to:

```json
{
  "status": "ACTIVE",
  "approved_by": "PLATFORM_ADMIN",
  "approved_at": "",
  "visible": true
}
```

Visibility rules now enforced:

- Platform Admin sees all products.
- Manufacturer sees:
  - all `ACTIVE` visible products
  - own non-active proposed/rejected products
- Client/public sees:
  - only `ACTIVE` visible products

## Dashboard / Navigation Status

Duplicate onboarding UI issue fixed:

- Removed manufacturer onboarding form from `modules/admin/dashboard.py`
- Kept onboarding form in separate onboarding route only

Current admin navigation:

- `Dashboard`
- `Products`
- `Product Approvals`
- `Manufacturers`
- `Onboarding`
- `My Actions`
- `Notifications`
- `System Health`

Current manufacturer navigation:

- `Dashboard`
- `Products`
- `Inventory`
- `Client Orders`
- `Mandi RFQ`
- `Ledger / Khata`
- `My Actions`
- `Notifications`
- `Onboarding`

Current route behavior:

- `Dashboard` is summary-only.
- `Onboarding` is the single onboarding page.
- `Product Approvals` is the approval queue.
- `Manufacturers` is the manufacturer registry maintenance page.

## Files Changed

- `services/manufacturer_onboarding_service.py`
- `services/drive_service.py`
- `services/access_portal_service.py`
- `services/product_catalog_service.py`
- `services/action_center_service.py`
- `services/catalog_service.py`
- `bootstrap/app_bootstrap.py`
- `bootstrap/route_registry.py`
- `modules/admin/dashboard.py`
- `modules/admin/product_approvals.py`
- `modules/admin/manufacturers.py`
- `modules/onboarding/manufacturer_onboarding.py`
- `modules/products/dashboard.py`
- `modules/client/dashboard.py`
- `modules/analytics/dashboard.py`
- `tests/helpers/fake_storage.py`
- `tests/test_access_portal.py`
- `tests/test_business_cleanup.py`

## Validation

### `python -m pytest tests/ -q`

```text
sssss........................................                            [100%]
40 passed, 5 skipped in 8.92s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
success
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blockers

These were not part of this fix pass and still need follow-up:

1. `admin_as_manufacturer` session acquisition is still partial.
2. Client order/ledger/notification RBAC filtering still needs a dedicated cleanup pass.
3. Shared-zone vs private-zone storage split is still not fully enforced for orders/inventory.
4. RFQ response pricing validation still needs strengthening before ledger creation.
5. Legacy agreement-era files still exist in the repository even though they are not in the active workflow.

## Acceptance Check

- manufacturer onboarding no longer enters approval pending status: `YES`
- newly onboarded manufacturer becomes `ACTIVE`: `YES`
- product proposal requires platform admin approval: `YES`
- `ACTIVE` products only are visible to clients/public users: `YES`
- dashboard no longer duplicates onboarding form: `YES`
- onboarding form remains available only through separate navigation: `YES`
- tests pass: `YES`
- app imports cleanly: `YES`
