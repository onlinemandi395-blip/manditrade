from __future__ import annotations

from typing import Any

from services.admin_drive_service import AdminDriveService


class ConfigLoaderService:
    DRIVE_PATHS = {
        "app_config": "00_config/app_config.json",
        "auth": "00_config/auth.json",
        "permissions": "00_config/permissions.json",
        "role_views": "00_config/role_views.json",
        "navigation": "00_config/navigation.json",
        "modules": "00_config/modules.json",
        "dashboards": "00_config/dashboards.json",
        "forms": "00_config/forms.json",
        "database": "00_config/database.json",
        "users": "01_identity/users.json",
        "product_mapping": "02_catalog/product_mapping.json",
        "raw_materials_data": "02_catalog/raw_materials.json",
        "orders_data": "05_orders/orders.json",
        "shipments_data": "06_shipments/shipments.json",
        "ledger_data": "07_ledger/ledger.json",
        "notifications_data": "09_notifications/notifications.json",
        "gmail_queue_data": "09_notifications/gmail_queue.json",
    }

    def __init__(self) -> None:
        self.admin_drive_service = AdminDriveService()

    def validate_runtime(self) -> dict[str, Any]:
        return self.admin_drive_service.get_runtime_manifest()

    def load(self, name: str) -> dict[str, Any]:
        logical_path = self.DRIVE_PATHS.get(name)
        if not logical_path:
            raise KeyError(f"Unsupported Drive config key: {name}")
        return self.admin_drive_service.read_json(logical_path)

    def load_language(self, code: str) -> dict[str, Any]:
        return self.admin_drive_service.read_json(f"00_config/languages/{code}.json")
