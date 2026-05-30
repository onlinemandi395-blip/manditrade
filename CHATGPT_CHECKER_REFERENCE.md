# MandiTrade Checker Reference

Generated from the current repository state on 2026-05-30 after the three-tier pricing and commission engine pass.

## Three-Tier Pricing Status

- Product pricing now supports:
  - `mandi_price`
  - `client_price`
  - `marketplace_price`
- Suggested and approved variants are supported in [services/product_catalog_service.py](C:/2026/manditrade/manditrade/services/product_catalog_service.py):
  - `suggested_mandi_price`
  - `suggested_client_price`
  - `suggested_marketplace_price`
  - `approved_mandi_price`
  - `approved_client_price`
  - `approved_marketplace_price`
- Backward compatibility remains for legacy `mrp` and `approved_mrp`, with `mrp` now aligned to `client_price`.

## RBAC Price Visibility Status

- Role-based product price visibility is enforced in [services/product_catalog_service.py](C:/2026/manditrade/manditrade/services/product_catalog_service.py).
- Platform admin and manufacturer/admin-as-manufacturer can retain internal pricing visibility.
- Private clients only receive client-facing pricing and `Your Price`.
- Public buyers only receive marketplace-facing pricing and `Price`.
- Client order query sanitization now strips mandi and marketplace pricing in [services/query/order_query_service.py](C:/2026/manditrade/manditrade/services/query/order_query_service.py).
- Client ledger view now hides commission and mandi-price internals through [services/ledger_service.py](C:/2026/manditrade/manditrade/services/ledger_service.py) and [modules/ledger/dashboard.py](C:/2026/manditrade/manditrade/modules/ledger/dashboard.py).

## Commission Engine Status

- The new commission engine lives in [services/pricing_service.py](C:/2026/manditrade/manditrade/services/pricing_service.py).
- Supported channels:
  - `MANDI`
  - `PRIVATE_CLIENT`
  - `PUBLIC_MARKETPLACE`
- Logic implemented:
  - private client profit = `client_price - mandi_price`
  - marketplace profit = `marketplace_price - mandi_price`
  - admin base commission = 50% of gross profit
  - manufacturer share = 50% of gross profit
  - platform fee on admin commission:
    - `basic = 10%`
    - `premium = 5%`
    - `premium_plus = 1%`
- Zero or negative profit returns zero commission and a pricing warning.
- Missing subscription defaults to `basic`.

## Order Flow Pricing Status

- Private client order rows now normalize to `client_price` in [services/order_transaction_service.py](C:/2026/manditrade/manditrade/services/order_transaction_service.py).
- Private client ledger amount uses `client_price * qty`.
- Public cart/order rows now normalize to marketplace pricing in:
  - [services/public_cart_service.py](C:/2026/manditrade/manditrade/services/public_cart_service.py)
  - [services/public_order_service.py](C:/2026/manditrade/manditrade/services/public_order_service.py)
- RFQ/procurement flow remains mandi-price based and does not apply downstream marketplace/client commission by default.

## Ledger Integration Status

- Ledger entries can now store internal channel and commission metadata through [services/ledger_service.py](C:/2026/manditrade/manditrade/services/ledger_service.py).
- Private-client order confirmation stores ledger metadata including:
  - `channel`
  - `mandi_price`
  - `sale_price`
  - `gross_profit`
  - `commission_breakdown`
- Client ledger view strips the internal commission and mandi-price fields before display.

## UI Status

- Manufacturer/admin product screens now use three-tier labels in:
  - [modules/products/dashboard.py](C:/2026/manditrade/manditrade/modules/products/dashboard.py)
  - [modules/admin/product_approvals.py](C:/2026/manditrade/manditrade/modules/admin/product_approvals.py)
- Public marketplace cards now show only marketplace `Price` in [modules/marketplace/dashboard.py](C:/2026/manditrade/manditrade/modules/marketplace/dashboard.py).
- Pricing sandbox page now uses the new pricing service in [modules/pricing/dashboard.py](C:/2026/manditrade/manditrade/modules/pricing/dashboard.py).

## Tests Result

### `python -m pytest tests/ -q`

```text
sssss................................................................... [ 75%]
........................                                                 [100%]
91 passed, 5 skipped in 17.21s
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

- The private-client order creation path currently stores commission breakdown internally, but there is not yet a dedicated manufacturer-facing commission analytics screen per order/channel beyond the product and ledger surfaces already updated.
