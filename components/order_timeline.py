from __future__ import annotations

import streamlit as st

DEFAULT_TIMELINE_STEPS = [
    "PLACED",
    "VALIDATED",
    "CONFIRMED",
    "PROCUREMENT_REQUIRED",
    "AGREEMENT_PENDING",
    "ADVANCE_PENDING",
    "DISPATCH_READY",
    "DISPATCHED",
    "DELIVERED",
    "CLOSED",
]


def render_order_timeline_component(status: str, *, steps: list[str] | None = None, labels: dict[str, str] | None = None) -> None:
    timeline_steps = steps or DEFAULT_TIMELINE_STEPS
    current_index = timeline_steps.index(status) if status in timeline_steps else 0
    cols = st.columns(len(timeline_steps))
    for index, step in enumerate(timeline_steps):
        complete = index <= current_index
        color = "#16a34a" if complete else "#64748b"
        label = (labels or {}).get(step, step)
        cols[index].markdown(
            f"""
            <div style="text-align:center;">
              <div style="width:18px;height:18px;margin:0 auto 8px;background:{color};border-radius:999px;"></div>
              <div style="font-size:0.72rem;color:{color};font-weight:700;">{label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
