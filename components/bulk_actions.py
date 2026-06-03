from __future__ import annotations

from typing import Any

import streamlit as st


def render_bulk_actions(
    *,
    page_key: str,
    rows: list[dict[str, Any]],
    id_field: str,
    action_options: list[tuple[str, str]],
    selection_label: str,
) -> tuple[list[str], str | None]:
    if not rows:
        return [], None
    selected_ids = st.multiselect(
        selection_label,
        options=[str(item.get(id_field, "")) for item in rows if item.get(id_field)],
        key=f"{page_key}_selected_ids",
    )
    action = st.selectbox(
        "Bulk action",
        options=[""] + [value for value, _label in action_options],
        format_func=lambda value: "Choose action" if value == "" else dict(action_options).get(value, value),
        key=f"{page_key}_bulk_action",
    )
    triggered = None
    if st.button("Run Bulk Action", key=f"{page_key}_bulk_action_run", use_container_width=True):
        triggered = action or None
    return selected_ids, triggered
