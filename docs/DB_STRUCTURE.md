# Database Structure

Current data collections:

- `users` -> `MANDITRADE_DB/01_identity/users.json`
- `products` -> `MANDITRADE_DB/02_catalog/product_mapping.json`
- `raw_materials` -> `MANDITRADE_DB/02_catalog/raw_materials.json`
- `orders` -> `MANDITRADE_DB/05_orders/orders.json`
- `shipments` -> `MANDITRADE_DB/06_shipments/shipments.json`
- `ledger` -> `MANDITRADE_DB/07_ledger/ledger.json`
- `notifications` -> `MANDITRADE_DB/09_notifications/notifications.json`
- `gmail_queue` -> `MANDITRADE_DB/09_notifications/gmail_queue.json`

Configuration files are loaded from:

- `MANDITRADE_DB/00_config/app_config.json`
- `MANDITRADE_DB/00_config/auth.json`
- `MANDITRADE_DB/00_config/permissions.json`
- `MANDITRADE_DB/00_config/role_views.json`
- `MANDITRADE_DB/00_config/navigation.json`
- `MANDITRADE_DB/00_config/modules.json`
- `MANDITRADE_DB/00_config/dashboards.json`
- `MANDITRADE_DB/00_config/forms.json`
- `MANDITRADE_DB/00_config/database.json`
- `MANDITRADE_DB/00_config/languages/*.json`

Storage mode is `drive_only`.
