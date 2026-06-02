from __future__ import annotations

from typing import Iterable

import streamlit as st

from services.session_state_service import SessionStateService
from utils.status_styles import get_status_style

_SESSION_STATE = SessionStateService()


def render_page_hero(*, title: str, subtitle: str, role_label: str = "", description: str = "") -> None:
    st.subheader(title)
    if role_label:
        st.caption(f"{role_label} | {subtitle}")
    else:
        st.caption(subtitle)
    if description:
        st.write(description)


def _state_key(page_key: str, suffix: str) -> str:
    return f"page_ui::{page_key}::{suffix}"


def set_active_tab_from_metric(page_key: str, tab_name: str, *, filter_value: str = "") -> None:
    st.session_state[_state_key(page_key, "tab")] = tab_name
    _SESSION_STATE.set_active_tab(page_key, tab_name)
    if filter_value:
        st.session_state[_state_key(page_key, "filter")] = filter_value
        current_filters = _SESSION_STATE.get_filters(page_key)
        current_filters["metric_filter"] = filter_value
        _SESSION_STATE.set_filters(page_key, current_filters)


def get_active_filter(page_key: str) -> str:
    return str(st.session_state.get(_state_key(page_key, "filter"), ""))


def render_metric_card_button(
    *,
    page_key: str,
    label: str,
    value: str,
    tab_name: str,
    filter_value: str = "",
    help_text: str = "",
    button_key: str | None = None,
) -> bool:
    button_label = f"{label}\n{value}"
    clicked = st.button(
        button_label,
        key=button_key or f"{page_key}_{label.lower().replace(' ', '_')}",
        help=help_text or f"Open {tab_name}",
        use_container_width=True,
    )
    if clicked:
        set_active_tab_from_metric(page_key, tab_name, filter_value=filter_value)
    return clicked


def render_metric_button_row(page_key: str, metrics: Iterable[dict]) -> None:
    items = list(metrics)
    columns = st.columns(len(items)) if items else []
    for column, metric in zip(columns, items):
        with column:
            render_metric_card_button(
                page_key=page_key,
                label=str(metric.get("label", "")),
                value=str(metric.get("value", "")),
                tab_name=str(metric.get("tab_name", "Overview")),
                filter_value=str(metric.get("filter_value", "")),
                help_text=str(metric.get("help_text", "")),
                button_key=metric.get("button_key"),
            )


def render_empty_state(message: str, *, action_label: str = "", action_key: str = "", disabled: bool = True) -> bool:
    st.info(message)
    if action_label:
        return st.button(action_label, key=action_key or action_label.lower().replace(" ", "_"), use_container_width=True, disabled=disabled)
    return False


def render_status_chip(label: str, value: str) -> None:
    style = get_status_style(value)
    st.markdown(
        f"""
        <div style="display:inline-flex;align-items:center;gap:0.5rem;margin:0.2rem 0 0.55rem 0;">
          <span style="font-size:0.8rem;color:#475569;">{label}:</span>
          <span style="padding:0.25rem 0.55rem;border-radius:999px;background:{style['background']};color:{style['color']};font-size:0.78rem;font-weight:700;">
            {value}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
