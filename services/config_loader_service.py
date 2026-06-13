from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.admin_drive_service import AdminDriveService
from services.performance_service import PerformanceService


class ConfigLoaderService:
    LOCAL_CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
    LOCAL_LANGUAGE_DIR = Path(__file__).resolve().parent.parent / "configs" / "languages"
    DRIVE_PATHS = {
        "app_config": "00_config/app_config.json",
        "auth": "00_config/auth.json",
        "permissions": "00_config/permissions.json",
        "role_views": "00_config/role_views.json",
        "navigation": "00_config/navigation.json",
        "modules": "00_config/modules.json",
        "dashboards": "00_config/dashboards.json",
        "forms": "00_config/forms.json",
        "categories": "00_config/categories.json",
        "payment_config": "00_config/payment_config.json",
        "database": "00_config/database.json",
        "theme": "00_config/theme.json",
        "users": "01_identity/users.json",
        "products_data": "02_catalog/products.json",
        "marketplace_orders_data": "05_orders/marketplace/orders.json",
        "manditrade_orders_data": "05_orders/mandiplace/orders.json",
        "payments_data": "07_ledger/payments.json",
        "shipments_data": "06_shipments/shipments.json",
        "ledger_data": "07_ledger/ledger.json",
        "notifications_data": "09_notifications/notifications.json",
        "gmail_queue_data": "09_notifications/gmail_queue.json",
        "audit_logs_data": "10_audit/audit_logs.json",
    }

    def __init__(self) -> None:
        self.admin_drive_service = AdminDriveService()
        self.performance_service = PerformanceService()

    def validate_runtime(self) -> dict[str, Any]:
        return self.admin_drive_service.get_runtime_manifest()

    def load(self, name: str) -> dict[str, Any]:
        logical_path = self.DRIVE_PATHS.get(name)
        if not logical_path:
            raise KeyError(f"Unsupported Drive config key: {name}")
        with self.performance_service.measure(f"load_{name}"):
            payload = self.admin_drive_service.read_json(logical_path)
        if name == "app_config":
            local_payload = self._load_local_config_bundle("app_config")
            return self._deep_merge(local_payload, payload)
        return payload

    def load_language(self, code: str) -> dict[str, Any]:
        drive_bundle: dict[str, Any] = {}
        with self.performance_service.measure(f"language_load_{code}"):
            try:
                payload = self.admin_drive_service.read_json(f"00_config/languages/{code}.json")
                drive_bundle = dict(payload.get("translations", payload))
            except FileNotFoundError:
                drive_bundle = {}
        local_bundle = self._load_local_language_bundle(code)
        merged = dict(drive_bundle)
        merged.update(local_bundle)
        return merged

    def list_available_language_codes(self) -> list[str]:
        discovered_codes = {
            path.stem.strip().lower()
            for path in self.LOCAL_LANGUAGE_DIR.glob("*.json")
            if path.stem.strip()
        }
        try:
            resolver = self.admin_drive_service.get_path_resolver()
            folder = resolver.resolve_folder_path("00_config/languages")
            if folder.get("status") == "FOUND":
                for row in self.admin_drive_service.google_drive_service.list_children(
                    resolver.service,
                    folder["folder_id"],
                ):
                    name = str(row.get("name", "")).strip()
                    if name.lower().endswith(".json"):
                        discovered_codes.add(name[:-5].strip().lower())
        except Exception:
            pass
        return sorted(code for code in discovered_codes if code)

    def _load_local_language_bundle(self, code: str) -> dict[str, Any]:
        path = self.LOCAL_LANGUAGE_DIR / f"{code}.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload.get("translations", payload))

    def _load_local_config_bundle(self, name: str) -> dict[str, Any]:
        path = self.LOCAL_CONFIG_DIR / f"{name}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base or {})
        for key, value in dict(override or {}).items():
            if isinstance(merged.get(key), dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(dict(merged[key]), value)
            else:
                merged[key] = value
        return merged
