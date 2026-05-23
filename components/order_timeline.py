from __future__ import annotations

import streamlit as st


TIMELINE_STEPS = [
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


def render_order_timeline_component(status: str) -> None:
    current_index = TIMELINE_STEPS.index(status) if status in TIMELINE_STEPS else 0
    cols = st.columns(len(TIMELINE_STEPS))
    for index, step in enumerate(TIMELINE_STEPS):
        complete = index <= current_index
        color = "#16a34a" if complete else "#64748b"
        cols[index].markdown(
            f"""
            <div style="text-align:center;">
              <div style="width:18px;height:18px;margin:0 auto 8px;background:{color};border-radius:999px;"></div>
              <div style="font-size:0.72rem;color:{color};font-weight:700;">{step}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
