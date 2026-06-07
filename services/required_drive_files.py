from __future__ import annotations


def build_required_drive_files(primary_admin_email: str, primary_admin_name: str) -> list[dict]:
    return [
        {
            "logical_path": "00_config/app_config.json",
            "type": "config",
            "default_payload": {
                "app_name": "MandiTrade Next",
                "version": "0.1.0",
                "default_role": "public_buyer",
                "default_language": "en",
                "default_landing": {
                    "platform_admin": "dashboard",
                    "manufacturer": "dashboard",
                    "mahajan": "dashboard",
                    "delivery_partner": "dashboard",
                    "public_buyer": "marketplace",
                    "worker": "dashboard",
                },
                "storage_mode": "google_drive_only",
                "admin_drive_enabled": True,
                "debug_auth": True,
            },
        },
        {
            "logical_path": "00_config/auth.json",
            "type": "config",
            "default_payload": {
                "authentication": {
                    "unknown_user_default_role": "public_buyer",
                    "providers": [
                        {
                            "provider_id": "google",
                            "enabled": True,
                            "icon": "[G]",
                            "label_key": "auth.login_google",
                        }
                    ],
                    "login_page": {
                        "title_key": "auth.title",
                        "subtitle_key": "auth.subtitle",
                        "show_language_selector": True,
                        "features": [],
                    },
                }
            },
        },
        {
            "logical_path": "00_config/permissions.json",
            "type": "config",
            "default_payload": {
                "permissions": {
                    "platform_admin": ["*"],
                    "manufacturer": ["dashboard", "products", "marketplace", "manditrade", "orders", "notifications", "shipments", "ledger"],
                    "mahajan": ["dashboard", "products", "manditrade", "orders", "notifications", "shipments", "ledger"],
                    "delivery_partner": ["dashboard", "shipments", "completed_deliveries", "notifications"],
                    "public_buyer": ["marketplace", "orders", "notifications"],
                    "worker": ["dashboard", "notifications"],
                }
            },
        },
        {
            "logical_path": "00_config/role_views.json",
            "type": "config",
            "default_payload": {
                "role_views": {
                    "platform_admin": {"landing_page": "dashboard"},
                    "manufacturer": {"landing_page": "dashboard"},
                    "mahajan": {"landing_page": "dashboard"},
                    "delivery_partner": {"landing_page": "dashboard"},
                    "public_buyer": {"landing_page": "marketplace"},
                    "worker": {"landing_page": "dashboard"},
                }
            },
        },
        {
            "logical_path": "00_config/navigation.json",
            "type": "config",
            "default_payload": {
                "navigation": {
                    "items": [
                        {"route": "dashboard", "icon": "[DB]", "label_key": "sidebar.dashboard"},
                        {"route": "products", "icon": "[PD]", "label_key": "sidebar.products"},
                        {"route": "marketplace", "icon": "[MK]", "label_key": "sidebar.marketplace"},
                        {"route": "manditrade", "icon": "[MT]", "label_key": "sidebar.manditrade"},
                        {"route": "orders", "icon": "[OR]", "label_key": "sidebar.orders"},
                        {"route": "payments", "icon": "[PY]", "label_key": "sidebar.payments"},
                        {"route": "shipments", "icon": "[SH]", "label_key": "sidebar.shipments"},
                        {"route": "completed_deliveries", "icon": "[CD]", "label_key": "sidebar.completed_deliveries"},
                        {"route": "ledger", "icon": "[LG]", "label_key": "sidebar.ledger"},
                        {"route": "notifications", "icon": "[NT]", "label_key": "sidebar.notifications"},
                        {"route": "admin_configuration", "icon": "[CF]", "label_key": "sidebar.admin_configuration"},
                        {"route": "system_health", "icon": "[HL]", "label_key": "sidebar.system_health"},
                    ]
                }
            },
        },
        {
            "logical_path": "00_config/modules.json",
            "type": "config",
            "default_payload": {
                "modules": {
                    "dashboard": {"type": "dashboard", "title_key": "module.dashboard.title", "subtitle_key": "module.dashboard.subtitle", "visible_to": ["platform_admin", "manufacturer", "mahajan", "delivery_partner", "worker"]},
                    "products": {"type": "products_admin", "title_key": "module.products.title", "subtitle_key": "module.products.subtitle", "data_source": "products", "visible_to": ["platform_admin", "manufacturer", "mahajan"]},
                    "marketplace": {"type": "product_grid", "title_key": "module.marketplace.title", "subtitle_key": "module.marketplace.subtitle", "data_source": "products", "visible_to": ["platform_admin", "public_buyer", "manufacturer"], "filters": {"sales_channels.marketplace.enabled": True}},
                    "manditrade": {"type": "manditrade", "title_key": "module.manditrade.title", "subtitle_key": "module.manditrade.subtitle", "data_source": "products", "visible_to": ["platform_admin", "manufacturer", "mahajan"], "filters": {"sales_channels.manditrade.enabled": True}},
                    "orders": {"type": "table", "title_key": "module.orders.title", "subtitle_key": "module.orders.subtitle", "data_source": "orders", "visible_to": ["platform_admin", "manufacturer", "mahajan", "public_buyer"]},
                    "payments": {"type": "table", "title_key": "module.payments.title", "subtitle_key": "module.payments.subtitle", "data_source": "payments", "visible_to": ["platform_admin"]},
                    "notifications": {"type": "table", "title_key": "module.notifications.title", "subtitle_key": "module.notifications.subtitle", "data_source": "notifications", "visible_to": ["platform_admin", "manufacturer", "mahajan", "delivery_partner", "public_buyer", "worker"]},
                    "admin_configuration": {"type": "admin_configuration", "title_key": "module.admin_configuration.title", "subtitle_key": "module.admin_configuration.subtitle", "visible_to": ["platform_admin"]},
                    "system_health": {"type": "system", "title_key": "module.system_health.title", "subtitle_key": "module.system_health.subtitle", "visible_to": ["platform_admin"]},
                    "shipments": {"type": "table", "title_key": "module.shipments.title", "subtitle_key": "module.shipments.subtitle", "data_source": "shipments", "visible_to": ["platform_admin", "manufacturer", "mahajan", "delivery_partner"]},
                    "completed_deliveries": {"type": "completed_deliveries_page", "title_key": "module.completed_deliveries.title", "subtitle_key": "module.completed_deliveries.subtitle", "data_source": "shipments", "visible_to": ["delivery_partner"]},
                    "ledger": {"type": "ledger_page", "title_key": "module.ledger.title", "subtitle_key": "module.ledger.subtitle", "data_source": "ledger", "visible_to": ["platform_admin", "manufacturer", "mahajan"]},
                }
            },
        },
        {
            "logical_path": "00_config/dashboards.json",
            "type": "config",
            "default_payload": {
                "dashboards": {
                    "platform_admin": {
                        "cards": [
                            {"id": "products_count", "title_key": "dashboard.products", "icon": "[PD]", "data_source": "products", "metric": "count", "route": "products"},
                            {"id": "orders_count", "title_key": "dashboard.orders", "icon": "[OR]", "data_source": "orders", "metric": "count", "route": "orders"},
                            {"id": "open_ledger", "title_key": "dashboard.open_ledger", "icon": "[LG]", "data_source": "ledger", "metric": "count", "route": "ledger"},
                        ]
                    },
                    "manufacturer": {
                        "cards": [
                            {"id": "my_products", "title_key": "dashboard.my_products", "icon": "[PD]", "data_source": "products", "metric": "owned_products", "route": "products"},
                            {"id": "orders_received", "title_key": "dashboard.orders_received", "icon": "[OR]", "data_source": "orders", "metric": "orders_received", "route": "orders"},
                            {"id": "pending_orders", "title_key": "dashboard.pending_orders", "icon": "[OR]", "data_source": "orders", "metric": "pending_orders", "route": "orders"},
                            {"id": "completed_orders", "title_key": "dashboard.completed_orders", "icon": "[OR]", "data_source": "orders", "metric": "completed_orders", "route": "orders"},
                            {"id": "ledger_balance", "title_key": "dashboard.ledger_balance", "icon": "[LG]", "data_source": "ledger", "metric": "ledger_balance", "route": "ledger"},
                            {"id": "unread_notifications", "title_key": "dashboard.unread_notifications", "icon": "[NT]", "data_source": "notifications", "metric": "unread_notifications", "route": "notifications"},
                        ]
                    },
                    "mahajan": {
                        "cards": [
                            {"id": "mahajan_products", "title_key": "dashboard.my_products", "icon": "[PD]", "data_source": "products", "metric": "owned_products", "route": "products"},
                            {"id": "orders_received", "title_key": "dashboard.orders_received", "icon": "[OR]", "data_source": "orders", "metric": "orders_received", "route": "orders"},
                            {"id": "pending_orders", "title_key": "dashboard.pending_orders", "icon": "[OR]", "data_source": "orders", "metric": "pending_orders", "route": "orders"},
                            {"id": "completed_orders", "title_key": "dashboard.completed_orders", "icon": "[OR]", "data_source": "orders", "metric": "completed_orders", "route": "orders"},
                            {"id": "ledger_balance", "title_key": "dashboard.ledger_balance", "icon": "[LG]", "data_source": "ledger", "metric": "ledger_balance", "route": "ledger"},
                            {"id": "unread_notifications", "title_key": "dashboard.unread_notifications", "icon": "[NT]", "data_source": "notifications", "metric": "unread_notifications", "route": "notifications"},
                        ]
                    },
                    "delivery_partner": {
                        "cards": [
                            {"id": "assigned_pickups", "title_key": "dashboard.assigned_pickups", "icon": "[SH]", "data_source": "shipments", "metric": "count", "route": "shipments"},
                            {"id": "in_transit", "title_key": "dashboard.in_transit", "icon": "[SH]", "data_source": "shipments", "metric": "count", "route": "shipments"},
                            {"id": "unread_notifications", "title_key": "dashboard.unread_notifications", "icon": "[NT]", "data_source": "notifications", "metric": "unread_notifications", "route": "notifications"},
                        ]
                    },
                    "public_buyer": {"cards": [{"id": "catalog_count", "title_key": "dashboard.products", "icon": "[MK]", "data_source": "products", "metric": "count", "route": "marketplace"}]},
                    "worker": {"cards": [{"id": "worker_notifications", "title_key": "dashboard.notifications", "icon": "[NT]", "data_source": "notifications", "metric": "count", "route": "notifications"}]},
                }
            },
        },
        {
            "logical_path": "00_config/forms.json",
            "type": "config",
            "default_payload": {
                "forms": {
                    "product_form": {
                        "title_key": "form.product.title",
                        "submit_label_key": "action.save",
                        "collection": "products",
                        "fields": [],
                    }
                }
            },
        },
        {
            "logical_path": "00_config/categories.json",
            "type": "config",
            "default_payload": {
                "schema_version": 1,
                "categories": [
                    {"category": "Textile", "subcategories": ["Towel", "Bedsheet", "Curtain", "Blanket", "Fabric Roll", "Uniform"]},
                    {"category": "Raw Material", "subcategories": ["Cotton", "Thread", "Yarn", "Packaging", "Dye", "Chemical"]},
                    {"category": "Food Grain", "subcategories": ["Rice", "Wheat", "Pulses", "Maize", "Millet", "Flour"]},
                    {"category": "Industrial", "subcategories": ["Steel", "Machine Parts", "Tools", "Motor", "Pump", "Rack"]},
                    {"category": "Electronics", "subcategories": ["Mobile Accessories", "Wiring", "Switches", "LED", "Battery", "Charger"]},
                    {"category": "Packaging", "subcategories": ["Box", "Carton", "Bag", "Tape", "Label", "Bubble Wrap"]},
                    {"category": "Agriculture", "subcategories": ["Seeds", "Fertilizer", "Tools", "Irrigation", "Animal Feed"]},
                    {"category": "Construction", "subcategories": ["Cement", "Sand", "Bricks", "Tiles", "Paint", "Hardware"]},
                    {"category": "Furniture", "subcategories": ["Chair", "Table", "Rack", "Door", "Bed", "Cabinet"]},
                    {"category": "Other", "subcategories": ["General"]},
                ]
            },
        },
        {
            "logical_path": "00_config/payment_config.json",
            "type": "config",
            "default_payload": {
                "schema_version": 1,
                "payment": {
                    "upi_id": "manditrade@upi",
                    "payee_name": "MandiTrade",
                    "currency": "INR",
                    "enabled": True,
                },
            },
        },
        {
            "logical_path": "00_config/database.json",
            "type": "config",
            "default_payload": {
                "root": "MANDITRADE_DB",
                "storage_mode": "google_drive_only",
                "collections": {
                    "users": "users:users",
                    "products": "products_data:products",
                    "marketplace_orders": "marketplace_orders_data:orders",
                    "manditrade_orders": "manditrade_orders_data:orders",
                    "payments": "payments_data:payments",
                    "shipments": "shipments_data:shipments",
                    "ledger": "ledger_data:ledger",
                    "notifications": "notifications_data:notifications",
                    "gmail_queue": "gmail_queue_data:gmail_queue",
                },
            },
        },
        {
            "logical_path": "00_config/theme.json",
            "type": "config",
            "default_payload": {
                "schema_version": 1,
                "theme": {
                    "background": {
                        "enabled": False,
                        "source": "drive",
                        "file_id": "",
                        "file_name": "app_background.png",
                        "local_cache_key": "app_background",
                        "opacity": 0.35,
                        "overlay": "linear-gradient(rgba(3,7,18,0.82), rgba(3,7,18,0.9))",
                        "position": "center center",
                        "size": "cover",
                        "repeat": "no-repeat",
                    }
                },
            },
        },
        {
            "logical_path": "00_config/id_counters.json",
            "type": "config",
            "default_payload": {
                "schema_version": 1,
                "counters": {
                    "product": 0,
                    "user": 0,
                    "image": 0,
                    "payment_reference": 0,
                    "marketplace_order": 0,
                    "manditrade_order": 0,
                },
            },
        },
        {
            "logical_path": "00_config/languages/en.json",
            "type": "language",
            "default_payload": {
                "translations": {
                    "auth.title": "Welcome to MandiTrade",
                    "auth.subtitle": "Google Drive powered commerce platform",
                    "auth.login_google": "Continue with Google",
                    "role.delivery_partner": "Delivery Partner",
                    "role.delivery_partner.desc": "Assigned pickup and delivery partner",
                    "sidebar.dashboard": "Dashboard",
                    "sidebar.products": "Products",
                    "sidebar.marketplace": "Marketplace",
                    "sidebar.manditrade": "MandiTrade",
                    "sidebar.orders": "Orders",
                    "sidebar.payments": "Payments",
                    "sidebar.notifications": "Notifications",
                    "sidebar.completed_deliveries": "Completed Deliveries",
                    "sidebar.admin_configuration": "Admin Configuration",
                    "sidebar.system_health": "System Health",
                    "sidebar.shipments": "Shipments",
                    "sidebar.ledger": "Ledger",
                    "module.dashboard.title": "Dashboard",
                    "module.products.title": "Products",
                    "module.marketplace.title": "Marketplace",
                    "module.manditrade.title": "MandiTrade",
                    "module.orders.title": "Orders",
                    "module.payments.title": "Payments",
                    "module.payments.subtitle": "Verify incoming payments and payment references",
                    "module.completed_deliveries.title": "Completed Deliveries",
                    "module.completed_deliveries.subtitle": "Delivered orders assigned to you",
                    "module.notifications.title": "Notifications",
                    "module.admin_configuration.title": "Admin Configuration",
                    "module.system_health.title": "System Health",
                    "module.shipments.title": "Shipments",
                    "module.ledger.title": "Ledger",
                    "dashboard.products": "Products",
                    "dashboard.orders": "Orders",
                    "dashboard.my_products": "My Products",
                    "dashboard.orders_received": "Orders Received",
                    "dashboard.pending_orders": "Pending Orders",
                    "dashboard.completed_orders": "Completed Orders",
                    "dashboard.ledger_balance": "Ledger Balance",
                    "dashboard.open_ledger": "Open Ledger",
                    "dashboard.pending_owner_requests": "Pending Owner Requests",
                    "dashboard.unread_notifications": "Unread Notifications",
                    "dashboard.assigned_pickups": "Assigned Pickups",
                    "dashboard.in_transit": "In Transit",
                }
            },
        },
        {"logical_path": "00_config/languages/hi.json", "type": "language", "default_payload": {"translations": {}}},
        {"logical_path": "00_config/languages/mr.json", "type": "language", "default_payload": {"translations": {}}},
        {"logical_path": "00_config/languages/bn.json", "type": "language", "default_payload": {"translations": {}}},
        {
            "logical_path": "01_identity/users.json",
            "type": "data",
            "default_payload": {
                "users": [
                    {
                        "user_id": "USR_0001",
                        "email": primary_admin_email,
                        "role": "platform_admin",
                        "status": "ACTIVE",
                        "display_name": primary_admin_name or "Primary Admin",
                        "source": "toml_primary_admin",
                    }
                ] if primary_admin_email else []
            },
        },
        {"logical_path": "02_catalog/products.json", "type": "data", "default_payload": {"products": []}},
        {"logical_path": "05_orders/marketplace/orders.json", "type": "data", "default_payload": {"schema_version": 1, "orders": []}},
        {"logical_path": "05_orders/mandiplace/orders.json", "type": "data", "default_payload": {"schema_version": 1, "orders": []}},
        {"logical_path": "06_shipments/shipments.json", "type": "data", "default_payload": {"shipments": []}},
        {"logical_path": "07_ledger/ledger.json", "type": "data", "default_payload": {"ledger": []}},
        {"logical_path": "07_ledger/payments.json", "type": "data", "default_payload": {"payments": []}},
        {"logical_path": "09_notifications/notifications.json", "type": "data", "default_payload": {"notifications": []}},
        {"logical_path": "09_notifications/gmail_queue.json", "type": "data", "default_payload": {"gmail_queue": []}},
    ]
