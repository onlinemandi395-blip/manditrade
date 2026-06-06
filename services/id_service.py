from __future__ import annotations

from copy import deepcopy

import streamlit as st


class IdService:
    COUNTER_PATH = "00_config/id_counters.json"

    def __init__(self) -> None:
        st.session_state.setdefault("mt_next_ids", {})

    def next(self, prefix: str) -> str:
        counters = st.session_state["mt_next_ids"]
        counters[prefix] = int(counters.get(prefix, 0)) + 1
        return f"{prefix.upper()}_{counters[prefix]:04d}"

    def _read_drive_counters(self, admin_drive_service) -> dict:
        payload = admin_drive_service.read_json(self.COUNTER_PATH)
        counters = deepcopy(payload.get("counters", {}) or {})
        return {
            "schema_version": int(payload.get("schema_version", 1) or 1),
            "counters": {
                "product": int(counters.get("product", 0) or 0),
                "user": int(counters.get("user", 0) or 0),
                "image": int(counters.get("image", 0) or 0),
            },
        }

    def preview_drive_id(self, admin_drive_service, counter_name: str, prefix: str, width: int = 6) -> str:
        payload = self._read_drive_counters(admin_drive_service)
        next_value = int(payload["counters"].get(counter_name, 0)) + 1
        return f"{prefix}-{next_value:0{width}d}"

    def next_drive_id(self, admin_drive_service, counter_name: str, prefix: str, width: int = 6) -> str:
        payload = self._read_drive_counters(admin_drive_service)
        next_value = int(payload["counters"].get(counter_name, 0)) + 1
        payload["counters"][counter_name] = next_value
        admin_drive_service.write_json(self.COUNTER_PATH, payload)
        return f"{prefix}-{next_value:0{width}d}"
