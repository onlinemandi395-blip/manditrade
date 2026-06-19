from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import streamlit as st

from services.admin_drive_service import AdminDriveService
from services.performance_service import PerformanceService


class ConfigLoaderService:
    BOOTSTRAP_ROOT = Path(__file__).resolve().parent.parent / "bootstrap_seed"
    DEFAULT_BOOTSTRAP_MODE = "live"
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
        "product_owner_consent": "00_config/product_owner_consent.json",
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
        st.session_state.setdefault("mt_config_loader_cache", {})
        st.session_state.setdefault("mt_language_codes_cache", [])

    def _get_local_config_dir(self) -> Path:
        return self.BOOTSTRAP_ROOT / self.DEFAULT_BOOTSTRAP_MODE / "00_config"

    def _get_local_language_dir(self) -> Path:
        return self._get_local_config_dir() / "languages"

    def validate_runtime(self) -> dict[str, Any]:
        return self.admin_drive_service.get_runtime_manifest()

    def load(self, name: str) -> dict[str, Any]:
        cached_payload = st.session_state["mt_config_loader_cache"].get(name)
        if cached_payload is not None:
            return deepcopy(cached_payload)
        logical_path = self.DRIVE_PATHS.get(name)
        if not logical_path:
            raise KeyError(f"Unsupported Drive config key: {name}")
        with self.performance_service.measure(f"load_{name}"):
            payload = self.admin_drive_service.read_json(logical_path)
        if name == "app_config":
            local_payload = self._load_local_config_bundle("app_config")
            payload = self._deep_merge(local_payload, payload)
        st.session_state["mt_config_loader_cache"][name] = deepcopy(payload)
        return deepcopy(payload)

    def load_language(self, code: str) -> dict[str, Any]:
        cache_key = f"language::{str(code or '').strip().lower()}"
        cached_payload = st.session_state["mt_config_loader_cache"].get(cache_key)
        if cached_payload is not None:
            return deepcopy(cached_payload)
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
        st.session_state["mt_config_loader_cache"][cache_key] = deepcopy(merged)
        return deepcopy(merged)

    def list_available_language_codes(self) -> list[str]:
        cached_codes = list(st.session_state.get("mt_language_codes_cache", []) or [])
        if cached_codes:
            return cached_codes
        discovered_codes = {
            path.stem.strip().lower()
            for path in self._get_local_language_dir().glob("*.json")
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
        resolved_codes = sorted(code for code in discovered_codes if code)
        st.session_state["mt_language_codes_cache"] = resolved_codes
        return resolved_codes

    def _load_local_language_bundle(self, code: str) -> dict[str, Any]:
        path = self._get_local_language_dir() / f"{code}.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload.get("translations", payload))

    def _load_local_config_bundle(self, name: str) -> dict[str, Any]:
        path = self._get_local_config_dir() / f"{name}.json"
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
