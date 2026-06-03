from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from utils.page_ui import render_empty_state


def render_background_tasks_panel(app_context: dict, *, page_key: str = "background_tasks", limit: int = 20) -> None:
    tasks = app_context["background_task_service"].list_tasks(limit=limit)
    if not tasks:
        render_empty_state("No background tasks have been recorded yet.")
        return
    filtered = render_data_grid(
        page_key=page_key,
        rows=tasks,
        search_fields=["task_id", "task_type", "message", "created_by"],
        status_field="status",
        date_field="updated_at",
        search_placeholder="Search by task ID or task type",
    )
    if filtered:
        selected_id = st.selectbox(
            "Background Task",
            [item["task_id"] for item in filtered],
            key=f"{page_key}_selected_task",
        )
        selected = next(item for item in filtered if item["task_id"] == selected_id)
        st.json(selected, expanded=False)
