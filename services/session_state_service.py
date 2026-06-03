from __future__ import annotations

from typing import Any

import streamlit as st


class SessionStateService:
    PREFIX = "mt_state::"
    TRANSIENT_SIDEBAR_KEYS = {
        "sidebar_notifications_open",
        "sidebar_quick_actions_open",
        "sidebar_context_switch_open",
        "sidebar_mobile_overlay_open",
        "sidebar_expanded_groups",
        "sidebar_aux_panel",
    }
    TRANSIENT_PREFIXES = ("overlay::", "drawer::", "sidebar_overlay::", "sidebar_group::")
    DIRTY_FORMS_KEY = "dirty_forms"
    RECENT_SEARCHES_KEY = "recent_searches"

    def _key(self, name: str) -> str:
        return f"{self.PREFIX}{name}"

    def get(self, name: str, default: Any = None) -> Any:
        return st.session_state.get(self._key(name), default)

    def set(self, name: str, value: Any) -> None:
        st.session_state[self._key(name)] = value

    def get_active_role(self) -> str:
        return str(self.get("active_role", ""))

    def set_active_role(self, role: str) -> None:
        if role != self.get_active_role():
            self.collapse_transient_sidebar_state()
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
        if section != self.get_navigation(section):
            self.collapse_transient_sidebar_state()
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

    def add_recent_search(self, query: str, *, limit: int = 8) -> None:
        normalized = str(query or "").strip()
        if not normalized:
            return
        searches = [item for item in self.get(self.RECENT_SEARCHES_KEY, []) if item != normalized]
        searches.insert(0, normalized)
        self.set(self.RECENT_SEARCHES_KEY, searches[:limit])

    def get_recent_searches(self) -> list[str]:
        return list(self.get(self.RECENT_SEARCHES_KEY, []))

    def mark_unsaved_changes(self, form_key: str) -> None:
        dirty = dict(self.get(self.DIRTY_FORMS_KEY, {}))
        dirty[form_key] = {"active": True}
        self.set(self.DIRTY_FORMS_KEY, dirty)

    def clear_unsaved_changes(self, form_key: str) -> None:
        dirty = dict(self.get(self.DIRTY_FORMS_KEY, {}))
        if form_key in dirty:
            dirty.pop(form_key, None)
            self.set(self.DIRTY_FORMS_KEY, dirty)

    def has_unsaved_changes(self) -> bool:
        return any(bool(item.get("active")) for item in dict(self.get(self.DIRTY_FORMS_KEY, {})).values())

    def list_unsaved_forms(self) -> list[str]:
        return sorted(key for key, value in dict(self.get(self.DIRTY_FORMS_KEY, {})).items() if value.get("active"))

    def collapse_transient_sidebar_state(self) -> None:
        for key in self.TRANSIENT_SIDEBAR_KEYS:
            if key.endswith("_groups"):
                st.session_state[key] = {}
            else:
                st.session_state[key] = False
        for key in list(st.session_state.keys()):
            if key.startswith(self.PREFIX):
                inner = key[len(self.PREFIX):]
                if inner.startswith(self.TRANSIENT_PREFIXES):
                    st.session_state.pop(key, None)

    def clear_context(self) -> None:
        self.collapse_transient_sidebar_state()
        keys = [key for key in st.session_state if key.startswith(self.PREFIX)]
        for key in keys:
            st.session_state.pop(key, None)
