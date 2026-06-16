from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st


class CacheService:
    CORE_CONFIG_NAMES = (
        "app_config",
        "auth",
        "permissions",
        "role_views",
        "navigation",
        "modules",
        "dashboards",
        "forms",
        "database",
        "theme",
    )

    def __init__(self, config_loader_service) -> None:
        self.config_loader_service = config_loader_service
        self.cache_key = "mt_next_cache"
        self.drive_cache_key = "mt_drive_cache"

    def load_core_configs(self) -> dict:
        cache = st.session_state.get(self.cache_key, {})
        app_config = self.config_loader_service.load("app_config")
        cache = {
            **cache,
            "app_config": app_config,
            "auth": self.config_loader_service.load("auth"),
            "permissions": self.config_loader_service.load("permissions"),
            "role_views": self.config_loader_service.load("role_views"),
            "navigation": self.config_loader_service.load("navigation"),
            "modules": self.config_loader_service.load("modules"),
            "dashboards": self.config_loader_service.load("dashboards"),
            "forms": self.config_loader_service.load("forms"),
            "database": self.config_loader_service.load("database"),
            "theme": self.config_loader_service.load("theme"),
            "_loaded_at": datetime.now(UTC).isoformat(),
        }
        st.session_state[self.cache_key] = cache
        st.session_state[self.drive_cache_key] = cache
        return cache

    def load_all_configs(self) -> dict:
        cache = self.load_core_configs()
        for name in (
            "users",
            "categories",
            "payment_config",
            "product_owner_consent",
            "products_data",
            "marketplace_orders_data",
            "manditrade_orders_data",
            "payments_data",
            "shipments_data",
            "ledger_data",
            "notifications_data",
            "gmail_queue_data",
            "audit_logs_data",
        ):
            cache[name] = self.config_loader_service.load(name)
        languages = {
            code: self.config_loader_service.load_language(code)
            for code in self.config_loader_service.list_available_language_codes()
        }
        cache["languages"] = languages
        cache["_loaded_at"] = datetime.now(UTC).isoformat()
        st.session_state[self.cache_key] = cache
        st.session_state[self.drive_cache_key] = cache
        return cache

    def get_config(self, name: str):
        cache = st.session_state.get(self.cache_key)
        if not cache:
            cache = self.load_core_configs()
        if name not in cache:
            if name == "languages":
                cache[name] = {
                    code: self.config_loader_service.load_language(code)
                    for code in self.config_loader_service.list_available_language_codes()
                }
            elif name.startswith("language::"):
                cache[name] = self.config_loader_service.load_language(name.split("::", 1)[1])
            else:
                cache[name] = self.config_loader_service.load(name)
            cache["_loaded_at"] = datetime.now(UTC).isoformat()
            st.session_state[self.cache_key] = cache
            st.session_state[self.drive_cache_key] = cache
        return cache.get(name, {})

    def refresh_cache(self) -> dict:
        st.session_state[self.cache_key] = {}
        st.session_state[self.drive_cache_key] = {}
        return self.load_core_configs()

    def update_config(self, name: str, payload) -> None:
        cache = st.session_state.get(self.cache_key) or self.load_all_configs()
        cache[name] = payload
        cache["_loaded_at"] = datetime.now(UTC).isoformat()
        st.session_state[self.cache_key] = cache
        st.session_state[self.drive_cache_key] = cache

    def get_cache_status(self) -> dict:
        cache = st.session_state.get(self.cache_key, {})
        return {
            "loaded": bool(cache),
            "keys": sorted(cache.keys()),
            "loaded_at": cache.get("_loaded_at", ""),
        }
