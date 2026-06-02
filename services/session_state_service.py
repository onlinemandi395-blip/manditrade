from __future__ import annotations

from typing import Any

import streamlit as st


class SessionStateService:
    PREFIX = "mt_state::"

    def _key(self, name: str) -> str:
        return f"{self.PREFIX}{name}"

    def get(self, name: str, default: Any = None) -> Any:
        return st.session_state.get(self._key(name), default)

    def set(self, name: str, value: Any) -> None:
        st.session_state[self._key(name)] = value

    def get_active_role(self) -> str:
        return str(self.get("active_role", ""))

    def set_active_role(self, role: str) -> None:
        self.set("active_role", role)

    def set_active_order(self, order_id: str) -> None:
        self.set("active_order", order_id)

    def get_active_order(self) -> str:
        return str(self.get("active_order", ""))

    def get_filters(self, page_key: str) -> dict[str, Any]:
        return dict(self.get(f"filters::{page_key}", {}))

    def set_filters(self, page_key: str, filters: dict[str, Any]) -> None:
        self.set(f"filters::{page_key}", dict(filters))

    def set_active_tab(self, page_key: str, tab_name: str) -> None:
        self.set(f"tab::{page_key}", tab_name)

    def get_active_tab(self, page_key: str, default: str = "Overview") -> str:
        return str(self.get(f"tab::{page_key}", default))

    def set_navigation(self, section: str) -> None:
        self.set("navigation", section)
        st.session_state["sidebar_section"] = section

    def get_navigation(self, default: str = "Dashboard") -> str:
        return str(self.get("navigation", st.session_state.get("sidebar_section", default)))

    def set_deep_link(self, target_key: str, entity_id: str) -> None:
        self.set(f"deep_link::{target_key}", entity_id)

    def get_deep_link(self, target_key: str) -> str:
        return str(self.get(f"deep_link::{target_key}", ""))

    def set_search_state(self, query: str) -> None:
        self.set("search_query", query)

    def get_search_state(self) -> str:
        return str(self.get("search_query", ""))

    def clear_context(self) -> None:
        keys = [key for key in st.session_state if key.startswith(self.PREFIX)]
        for key in keys:
            st.session_state.pop(key, None)
