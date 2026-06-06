from __future__ import annotations

import streamlit as st

from services.theme_service import ThemeService


class IntegrationStatusService:
    def __init__(self, cache_service, admin_drive_service, gmail_queue_service, oauth_service, data_service) -> None:
        self.cache_service = cache_service
        self.admin_drive_service = admin_drive_service
        self.gmail_queue_service = gmail_queue_service
        self.oauth_service = oauth_service
        self.data_service = data_service

    def _get_platform_config(self) -> dict:
        return dict(st.secrets.get("platform", {})) if "platform" in st.secrets else {}

    def get_status(self) -> dict:
        drive_status = self.admin_drive_service.get_status()
        drive_manifest = self.admin_drive_service.get_runtime_manifest(force_refresh=True)
        gmail_enabled = self.gmail_queue_service.is_enabled()
        gmail_sender = self.gmail_queue_service.get_sender_email()
        platform = self._get_platform_config()
        users = self.data_service.list_collection("users")
        products = self.data_service.list_collection("products")
        orders = self.data_service.list_collection("orders")
        notifications = self.data_service.list_collection("notifications")
        gmail_queue = self.data_service.list_collection("gmail_queue")
        loaded_languages = sorted((self.cache_service.get_config("languages") or {}).keys())
        theme_status = ThemeService(self.admin_drive_service, self.cache_service).get_background_status()
        return {
            "google_oauth_status": "configured" if self.oauth_service.is_configured() else "missing",
            "google_drive_status": "connected" if drive_status.get("connected") else "disconnected",
            "drive_root_status": drive_status.get("root_folder_id") or drive_status.get("root_folder_name") or "missing",
            "drive_mode": drive_status.get("mode", "user_oauth_drive"),
            "admin_token_status": "available" if drive_status.get("admin_token_available") else "missing",
            "drive_write_test": drive_status.get("drive_write_test", "FAIL"),
            "gmail_send_scope": drive_status.get("gmail_send_scope", "missing"),
            "cache_status": self.cache_service.get_cache_status(),
            "gmail_status": "enabled" if gmail_enabled and gmail_sender else "disabled",
            "queue_count": len(gmail_queue),
            "notification_queue_count": len(notifications),
            "primary_admin_email": str(platform.get("primary_admin_email", "")),
            "primary_admin_name": str(platform.get("primary_admin_name", "") or ""),
            "loaded_collection_count": len(self.cache_service.get_config("database").get("collections", {})),
            "users_count": len(users),
            "products_count": len(products),
            "order_count": len(orders),
            "language_selected": st.session_state.get("mt_next_language", "en"),
            "available_languages": loaded_languages,
            "language_files_loaded": len(loaded_languages),
            "required_folders_count": len(drive_manifest.get("required_folders", [])),
            "required_files_count": len(drive_manifest.get("required_files", [])),
            "missing_files_count": len(drive_manifest.get("missing_files", [])),
            "required_files_status": "ok" if not drive_manifest.get("missing_files") else "missing",
            "required_files": drive_manifest.get("required_files", []),
            "required_folders": drive_manifest.get("required_folders", []),
            "missing_files": drive_manifest.get("missing_files", []),
            "theme_status": theme_status,
        }
