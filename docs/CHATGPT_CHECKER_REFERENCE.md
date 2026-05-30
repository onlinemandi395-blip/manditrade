# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the pilot blocker fix pass for RFQ pricing, storage separation, and dedicated SuperAdmin summaries.

## RFQ Pricing Validation Status

- RFQ supplier responses now require explicit priced items in [services/procurement_transaction_service.py](C:/2026/manditrade/manditrade/services/procurement_transaction_service.py).
- Response item validation now enforces:
  - `qty > 0`
  - `offered_unit_price > 0`
  - `total_price = qty * offered_unit_price`
- Buyer acceptance is blocked if priced RFQ items are missing or zero-valued.
- Mandi khata creation for RFQ acceptance now uses response `total_price` instead of a zero-value fallback.
- RFQ UI now shows a validation error banner in [modules/rfq/dashboard.py](C:/2026/manditrade/manditrade/modules/rfq/dashboard.py) when invalid priced responses are present.

## Shared vs Private Storage Separation Status

- Domain-path separation was tightened in [services/domain_paths_service.py](C:/2026/manditrade/manditrade/services/domain_paths_service.py).
- Inventory paths now distinguish:
  - full private dual inventory via `private_self_inventory_path`
  - shared mandi projection via `shared_mandi_inventory_projection_path`
- [services/dual_inventory_service.py](C:/2026/manditrade/manditrade/services/dual_inventory_service.py) now writes:
  - full self + mandi operational inventory to private zone
  - mandi-only projection to shared zone
- Private client order full documents remain in private zone through [services/order_transaction_service.py](C:/2026/manditrade/manditrade/services/order_transaction_service.py).
- Shared-zone monthly client-order files are now sanitized projections only.
- [services/query/order_query_service.py](C:/2026/manditrade/manditrade/services/query/order_query_service.py) now reads manufacturer private client-order docs instead of shared-zone projections.
- [services/query/inventory_query_service.py](C:/2026/manditrade/manditrade/services/query/inventory_query_service.py) now reads mandi-visible shared inventory projections only.

## Dedicated SuperAdmin Summary Modules

- SuperAdmin summary routes now use dedicated read-only modules:
  - [modules/admin/rfq_summary.py](C:/2026/manditrade/manditrade/modules/admin/rfq_summary.py)
  - [modules/admin/inventory_summary.py](C:/2026/manditrade/manditrade/modules/admin/inventory_summary.py)
  - [modules/admin/commission_summary.py](C:/2026/manditrade/manditrade/modules/admin/commission_summary.py)
- Route wiring was updated in [bootstrap/route_registry.py](C:/2026/manditrade/manditrade/bootstrap/route_registry.py).
- Summary rules now hold:
  - read-only
  - aggregate-only
  - no private client identities
  - no private ledger notes
  - no private payment proposals

## SuperAdmin Privacy Boundary

- SuperAdmin dashboards remain summary-only in [modules/admin/dashboard.py](C:/2026/manditrade/manditrade/modules/admin/dashboard.py).
- Dedicated admin summary pages and helper services do not expose:
  - client name
  - client email
  - client mobile
  - private shipping address
  - private negotiation comments
  - private payment proposal details

## Navigation Status

- SuperAdmin nav includes:
  - `Dashboard`
  - `My Profile`
  - `Products`
  - `Product Approvals`
  - `Manufacturers`
  - `Marketplace`
  - `Public Orders`
  - `RFQ`
  - `Inventory Summary`
  - `Commission Summary`
  - `Payments`
  - `My Actions`
  - `Notifications`
  - `System Health`
- Manufacturer/admin-as-manufacturer nav remains:
  - `Dashboard`
  - `My Profile`
  - `Products`
  - `Inventory`
  - `Clients`
  - `Client Orders`
  - `Ledger`
  - `RFQ`
  - `Marketplace`
  - `My Actions`
  - `Notifications`

## Tests Result

### `python -m pytest tests/ -q`

```text
sssss................................................................... [ 69%]
................................                                         [100%]
99 passed, 5 skipped in 23.25s
```

### `python -m compileall app.py modules services utils components schemas bootstrap scripts`

```text
passed
```

### `python -c "import app; print('app import ok')"`

```text
app import ok
```

## Remaining Blockers

- The codebase still uses the internal runtime role label `platform_admin` instead of a globally normalized `SUPER_ADMIN` constant.
- SuperAdmin analytics pages are now dedicated and safe, but they are still table-driven operational summaries rather than richer chart/reporting dashboards.
