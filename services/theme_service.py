from __future__ import annotations

import base64
from copy import deepcopy

import streamlit as st


class ThemeService:
    CACHE_KEY = "mt_next_theme_cache"
    LIST_CACHE_KEY = "mt_next_theme_backgrounds"
    SELECTED_THEME_KEY = "mt_next_selected_theme"
    BACKGROUND_FOLDER_PATH = "15_media/app_assets/backgrounds"

    def __init__(self, admin_drive_service, cache_service) -> None:
        self.admin_drive_service = admin_drive_service
        self.cache_service = cache_service
        st.session_state.setdefault(self.CACHE_KEY, {})

    def get_theme_config(self) -> dict:
        try:
            return self.cache_service.get_config("theme")
        except Exception:
            try:
                return self.admin_drive_service.read_json("00_config/theme.json")
            except Exception:
                return {}

    def _get_effective_background(self) -> dict:
        theme_payload = self.get_theme_config()
        background = dict(((theme_payload.get("theme") or {}).get("background") or {}))
        selected = dict(st.session_state.get(self.SELECTED_THEME_KEY, {}) or {})
        if selected.get("file_id"):
            background["enabled"] = True
            background["file_id"] = selected.get("file_id", background.get("file_id", ""))
            background["file_name"] = selected.get("file_name", background.get("file_name", ""))
            background["local_cache_key"] = f"theme_{selected.get('file_id', 'app_background')}"
        return background

    def get_selected_background(self) -> dict:
        return dict(st.session_state.get(self.SELECTED_THEME_KEY, {}) or {})

    def clear_theme_cache(self) -> None:
        st.session_state[self.CACHE_KEY] = {}

    def clear_background_list_cache(self) -> None:
        st.session_state.pop(self.LIST_CACHE_KEY, None)

    def clear_selected_background(self) -> None:
        st.session_state.pop(self.SELECTED_THEME_KEY, None)

    def get_active_background_file_id(self) -> str:
        return str(self._get_effective_background().get("file_id", "") or "").strip()

    def _load_background_data_url(self, background: dict) -> str:
        file_id = str(background.get("file_id", "") or "").strip()
        if not file_id:
            return ""
        cache_key = str(background.get("local_cache_key", "app_background") or "app_background")
        theme_cache = st.session_state.get(self.CACHE_KEY, {})
        cached = theme_cache.get(cache_key, {})
        if isinstance(cached, dict) and cached.get("data_url"):
            return str(cached.get("data_url", ""))
        service = self.admin_drive_service.build_client()
        image_bytes = self.admin_drive_service.google_drive_service.read_file_bytes(service, file_id)
        mime_type = "image/png"
        lowered_name = str(background.get("file_name", "") or "").lower()
        if lowered_name.endswith(".jpg") or lowered_name.endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif lowered_name.endswith(".webp"):
            mime_type = "image/webp"
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
        theme_cache[cache_key] = {
            "data_url": data_url,
            "bytes": image_bytes,
            "mime_type": mime_type,
            "file_id": file_id,
            "file_name": background.get("file_name", ""),
        }
        st.session_state[self.CACHE_KEY] = theme_cache
        return data_url

    def get_background_preview_bytes(self, background: dict) -> bytes:
        file_id = str(background.get("file_id", "") or "").strip()
        if not file_id:
            return b""
        cache_key = str(background.get("local_cache_key", f"theme_{file_id}") or f"theme_{file_id}")
        theme_cache = st.session_state.get(self.CACHE_KEY, {})
        cached = theme_cache.get(cache_key, {})
        if isinstance(cached, dict) and cached.get("bytes"):
            return bytes(cached.get("bytes") or b"")
        self._load_background_data_url(background)
        cached = st.session_state.get(self.CACHE_KEY, {}).get(cache_key, {})
        return bytes(cached.get("bytes") or b"")

    def get_background_style(self) -> dict:
        background = self._get_effective_background()
        if not background.get("enabled", False):
            return {"enabled": False, "data_url": "", "warning": ""}
        file_id = str(background.get("file_id", "") or "").strip()
        if not file_id:
            return {"enabled": False, "data_url": "", "warning": "Theme background file_id is missing in theme.json."}
        try:
            data_url = self._load_background_data_url(background)
        except Exception as exc:
            return {"enabled": False, "data_url": "", "warning": f"Theme background could not be loaded from Drive: {exc}"}
        return {
            "enabled": True,
            "data_url": data_url,
            "overlay": str(background.get("overlay", "linear-gradient(rgba(20,0,0,0.82), rgba(0,0,0,0.9))")),
            "opacity": background.get("opacity", 0.35),
            "position": str(background.get("position", "center center")),
            "size": str(background.get("size", "cover")),
            "repeat": str(background.get("repeat", "no-repeat")),
            "warning": "",
        }

    def get_background_status(self) -> dict:
        theme_payload = self.get_theme_config()
        background = self._get_effective_background()
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

    def list_available_backgrounds(self, *, force_refresh: bool = False) -> list[dict]:
        if not force_refresh and st.session_state.get(self.LIST_CACHE_KEY):
            return list(st.session_state.get(self.LIST_CACHE_KEY, []))
        try:
            resolver = self.admin_drive_service.get_path_resolver()
            folder = resolver.resolve_folder_path(self.BACKGROUND_FOLDER_PATH)
            if folder.get("status") != "FOUND":
                st.session_state[self.LIST_CACHE_KEY] = []
                return []
            rows = self.admin_drive_service.google_drive_service.list_children(
                resolver.service,
                folder["folder_id"],
                mime_prefix="image/",
            )
            backgrounds = [
                {
                    "file_id": row.get("id", ""),
                    "file_name": row.get("name", ""),
                    "mime_type": row.get("mimeType", ""),
                    "thumbnail_link": row.get("thumbnailLink", ""),
                    "web_view_link": row.get("webViewLink", ""),
                    "direct_render_url": f"https://drive.google.com/uc?export=view&id={row.get('id', '')}",
                    "modified_time": row.get("modifiedTime", ""),
                }
                for row in rows
            ]
            st.session_state[self.LIST_CACHE_KEY] = backgrounds
            return backgrounds
        except Exception:
            return []

    def set_selected_background(self, background: dict | None) -> None:
        st.session_state[self.SELECTED_THEME_KEY] = dict(background or {})

    def save_default_background(self, background: dict) -> None:
        theme_payload = self.get_theme_config()
        updated = dict(theme_payload or {})
        updated["schema_version"] = int(updated.get("schema_version", 1) or 1)
        updated["theme"] = dict(updated.get("theme", {}) or {})
        existing_background = deepcopy(updated["theme"].get("background", {}) or {})
        updated["theme"]["background"] = {
            "enabled": True,
            "source": "drive",
            "file_id": background.get("file_id", ""),
            "file_name": background.get("file_name", ""),
            "local_cache_key": f"theme_{background.get('file_id', 'app_background')}",
            "opacity": existing_background.get("opacity", 0.35),
            "overlay": existing_background.get("overlay", "linear-gradient(rgba(20,0,0,0.82), rgba(0,0,0,0.9))"),
            "position": existing_background.get("position", "center center"),
            "size": existing_background.get("size", "cover"),
            "repeat": existing_background.get("repeat", "no-repeat"),
        }
        self.admin_drive_service.write_json("00_config/theme.json", updated)
        self.cache_service.update_config("theme", updated)
        self.clear_theme_cache()
        self.set_selected_background(background)

    def build_background_css(self) -> str:
        style = self.get_background_style()
        if not style.get("enabled"):
            return ""
        return (
            "body, .stApp, [data-testid=\"stAppViewContainer\"] {"
            f"background: {style['overlay']}, url(\"{style['data_url']}\") {style['position']} / {style['size']} {style['repeat']} fixed !important;"
            "}"
        )
