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
                    "mahajan": ["dashboard", "products", "orders", "notifications", "shipments", "ledger"],
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
                    "dashboard": {"type": "dashboard", "title_key": "module.dashboard.title", "subtitle_key": "module.dashboard.subtitle", "visible_to": ["platform_admin", "manufacturer", "mahajan", "worker"]},
                    "products": {"type": "products_admin", "title_key": "module.products.title", "subtitle_key": "module.products.subtitle", "data_source": "products", "visible_to": ["platform_admin", "manufacturer", "mahajan"]},
                    "marketplace": {"type": "product_grid", "title_key": "module.marketplace.title", "subtitle_key": "module.marketplace.subtitle", "data_source": "products", "visible_to": ["platform_admin", "public_buyer", "manufacturer"], "filters": {"sales_channels.marketplace.enabled": True}},
                    "manditrade": {"type": "manditrade", "title_key": "module.manditrade.title", "subtitle_key": "module.manditrade.subtitle", "data_source": "products", "visible_to": ["platform_admin", "manufacturer", "mahajan"], "filters": {"sales_channels.manditrade.enabled": True}},
                    "orders": {"type": "table", "title_key": "module.orders.title", "subtitle_key": "module.orders.subtitle", "data_source": "orders", "visible_to": ["platform_admin", "manufacturer", "mahajan", "public_buyer"]},
                    "notifications": {"type": "table", "title_key": "module.notifications.title", "subtitle_key": "module.notifications.subtitle", "data_source": "notifications", "visible_to": ["platform_admin", "manufacturer", "mahajan", "public_buyer", "worker"]},
                    "admin_configuration": {"type": "admin_configuration", "title_key": "module.admin_configuration.title", "subtitle_key": "module.admin_configuration.subtitle", "visible_to": ["platform_admin"]},
                    "system_health": {"type": "system", "title_key": "module.system_health.title", "subtitle_key": "module.system_health.subtitle", "visible_to": ["platform_admin"]},
                    "shipments": {"type": "table", "title_key": "module.shipments.title", "subtitle_key": "module.shipments.subtitle", "data_source": "shipments", "visible_to": ["platform_admin", "manufacturer", "mahajan"]},
                    "ledger": {"type": "table", "title_key": "module.ledger.title", "subtitle_key": "module.ledger.subtitle", "data_source": "ledger", "visible_to": ["platform_admin", "manufacturer", "mahajan", "public_buyer"]},
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
                "categories": [
                    {"category": "Textile", "subcategories": ["Towel", "Bedsheet", "Curtain", "Blanket"]},
                    {"category": "Raw Material", "subcategories": ["Cotton", "Thread", "Yarn", "Packaging"]},
                    {"category": "Food Grain", "subcategories": ["Rice", "Wheat", "Pulses"]},
                    {"category": "Industrial", "subcategories": ["Steel", "Machine Parts", "Tools"]},
                ]
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
                    "orders": "orders_data:orders",
                    "shipments": "shipments_data:shipments",
                    "ledger": "ledger_data:ledger",
                    "notifications": "notifications_data:notifications",
                    "gmail_queue": "gmail_queue_data:gmail_queue",
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
                    "sidebar.dashboard": "Dashboard",
                    "sidebar.products": "Products",
                    "sidebar.marketplace": "Marketplace",
                    "sidebar.manditrade": "MandiTrade",
                    "sidebar.orders": "Orders",
                    "sidebar.notifications": "Notifications",
                    "sidebar.admin_configuration": "Admin Configuration",
                    "sidebar.system_health": "System Health",
                    "module.dashboard.title": "Dashboard",
                    "module.products.title": "Products",
                    "module.marketplace.title": "Marketplace",
                    "module.manditrade.title": "MandiTrade",
                    "module.orders.title": "Orders",
                    "module.notifications.title": "Notifications",
                    "module.admin_configuration.title": "Admin Configuration",
                    "module.system_health.title": "System Health",
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
                ]
                if primary_admin_email
                else []
            },
        },
        {"logical_path": "02_catalog/products.json", "type": "data", "default_payload": {"products": []}},
        {"logical_path": "05_orders/orders.json", "type": "data", "default_payload": {"orders": []}},
        {"logical_path": "06_shipments/shipments.json", "type": "data", "default_payload": {"shipments": []}},
        {"logical_path": "07_ledger/ledger.json", "type": "data", "default_payload": {"ledger": []}},
        {"logical_path": "09_notifications/notifications.json", "type": "data", "default_payload": {"notifications": []}},
        {"logical_path": "09_notifications/gmail_queue.json", "type": "data", "default_payload": {"gmail_queue": []}},
    ]
