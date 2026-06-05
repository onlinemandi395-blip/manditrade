from __future__ import annotations

import streamlit as st


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
        gmail_enabled = self.gmail_queue_service.is_enabled()
        gmail_sender = self.gmail_queue_service.get_sender_email()
        platform = self._get_platform_config()
        return {
            "google_oauth_status": "configured" if self.oauth_service.is_configured() else "missing",
            "google_drive_status": "connected" if drive_status.get("connected") else "disconnected",
            "drive_root_status": drive_status.get("root_folder_id") or drive_status.get("root_folder_name") or "missing",
            "cache_status": self.cache_service.get_cache_status(),
            "gmail_status": "enabled" if gmail_enabled and gmail_sender else "disabled",
            "queue_count": len(self.data_service.list_collection("gmail_queue")),
            "notification_queue_count": len(self.data_service.list_collection("notifications")),
            "primary_admin_email": str(platform.get("primary_admin_email", "") or dict(st.secrets.get("admin", {})).get("admin_email", "")),
            "primary_admin_name": str(platform.get("primary_admin_name", "") or ""),
        }
