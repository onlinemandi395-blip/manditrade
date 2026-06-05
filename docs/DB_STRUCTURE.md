# Database Structure

Current data collections:

- `products` -> `configs/product_mapping.json:products`
- `raw_materials` -> `configs/seed_data.json:raw_materials`
- `orders` -> session-backed runtime collection seeded from `configs/seed_data.json:orders`
- `notifications` -> session-backed runtime collection seeded from `configs/seed_data.json:notifications`
- `shipments` -> session-backed runtime collection seeded from `configs/seed_data.json:shipments`
- `ledger` -> session-backed runtime collection seeded from `configs/seed_data.json:ledger`

Storage mode is `local_json_first`.
