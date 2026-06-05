from __future__ import annotations

import streamlit as st


class AdminDriveService:
    def get_status(self) -> dict:
        secrets = dict(st.secrets.get("google_drive", {})) if "google_drive" in st.secrets else {}
        has_service_account = bool(str(secrets.get("service_account_json", "") or "").strip())
        root_folder_id = str(secrets.get("root_folder_id", "") or secrets.get("admin_db_root_folder_id", "") or "").strip()
        root_folder_name = str(secrets.get("root_folder_name", "") or secrets.get("admin_db_root_folder_name", "") or "").strip()
        has_root = bool(root_folder_id or root_folder_name)
        return {
            "connected": has_service_account and has_root,
            "mode": "service_account" if has_service_account else "local_json_first",
            "source": "streamlit_secrets" if has_service_account else "local_config",
            "root_folder_id": root_folder_id,
            "root_folder_name": root_folder_name,
        }
