from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.json_service import JsonService


class CacheService:
    def __init__(self) -> None:
        self.json_service = JsonService()

    @st.cache_data(show_spinner=False)
    def read_json_cached(_self, path_str: str, fallback: dict | list | None = None):
        path = Path(path_str)
        if not path.exists():
            return fallback if fallback is not None else {}
        return JsonService().read_json(path, fallback if fallback is not None else {})

    def get_json(self, path: Path, fallback=None):
        return self.read_json_cached(str(path), fallback)

    def clear(self) -> None:
        self.read_json_cached.clear()
