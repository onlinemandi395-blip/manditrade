from __future__ import annotations

import base64

import streamlit as st


class ThemeService:
    CACHE_KEY = "mt_next_theme_cache"

    def __init__(self, admin_drive_service, cache_service) -> None:
        self.admin_drive_service = admin_drive_service
        self.cache_service = cache_service
        st.session_state.setdefault(self.CACHE_KEY, {})

    def get_theme_config(self) -> dict:
        return self.cache_service.get_config("theme")

    def get_background_style(self) -> dict:
        theme_payload = self.get_theme_config()
        background = dict(((theme_payload.get("theme") or {}).get("background") or {}))
        if not background.get("enabled", False):
            return {"enabled": False, "data_url": "", "warning": ""}
        file_id = str(background.get("file_id", "") or "").strip()
        if not file_id:
            return {"enabled": False, "data_url": "", "warning": "Theme background file_id is missing in theme.json."}
        cache_key = str(background.get("local_cache_key", "app_background") or "app_background")
        theme_cache = st.session_state.get(self.CACHE_KEY, {})
        if cache_key not in theme_cache:
            try:
                service = self.admin_drive_service.build_client()
                image_bytes = self.admin_drive_service.google_drive_service.read_file_bytes(service, file_id)
                mime_type = "image/png"
                lowered_name = str(background.get("file_name", "") or "").lower()
                if lowered_name.endswith(".jpg") or lowered_name.endswith(".jpeg"):
                    mime_type = "image/jpeg"
                elif lowered_name.endswith(".webp"):
                    mime_type = "image/webp"
                data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                theme_cache[cache_key] = data_url
                st.session_state[self.CACHE_KEY] = theme_cache
            except Exception as exc:
                return {"enabled": False, "data_url": "", "warning": f"Theme background could not be loaded from Drive: {exc}"}
        return {
            "enabled": True,
            "data_url": theme_cache[cache_key],
            "overlay": str(background.get("overlay", "linear-gradient(rgba(3,7,18,0.82), rgba(3,7,18,0.9))")),
            "opacity": background.get("opacity", 0.35),
            "position": str(background.get("position", "center center")),
            "size": str(background.get("size", "cover")),
            "repeat": str(background.get("repeat", "no-repeat")),
            "warning": "",
        }

    def get_background_status(self) -> dict:
        theme_payload = self.get_theme_config()
        background = dict(((theme_payload.get("theme") or {}).get("background") or {}))
        status = {
            "theme_config_present": bool(theme_payload),
            "background_enabled": bool(background.get("enabled", False)),
            "background_source": str(background.get("source", "")),
            "background_file_id": str(background.get("file_id", "") or ""),
            "background_file_name": str(background.get("file_name", "") or ""),
            "cache_key": str(background.get("local_cache_key", "app_background") or "app_background"),
            "status": "MISSING",
            "message": "",
        }
        if not theme_payload:
            status["message"] = "theme.json is missing or empty."
            return status
        if not background:
            status["message"] = "theme.background config is missing."
            return status
        if not background.get("enabled", False):
            status["status"] = "DISABLED"
            status["message"] = "Background theme is disabled."
            return status
        if not status["background_file_id"]:
            status["message"] = "Theme background file_id is not configured."
            return status
        try:
            service = self.admin_drive_service.build_client()
            metadata = service.files().get(
                fileId=status["background_file_id"],
                fields="id,name,mimeType,modifiedTime",
            ).execute()
            status["status"] = "READY"
            status["message"] = "Background image is reachable in Drive."
            status["resolved_name"] = metadata.get("name", "")
            status["mime_type"] = metadata.get("mimeType", "")
            status["modified_time"] = metadata.get("modifiedTime", "")
            return status
        except Exception as exc:
            status["message"] = f"Background image could not be resolved from Drive: {exc}"
            return status

    def build_background_css(self) -> str:
        style = self.get_background_style()
        if not style.get("enabled"):
            return ""
        return (
            ".stApp {"
            f"background-image: {style['overlay']}, url(\"{style['data_url']}\");"
            f"background-size: {style['size']};"
            f"background-position: {style['position']};"
            f"background-repeat: {style['repeat']};"
            "background-attachment: fixed;"
            "}"
        )
