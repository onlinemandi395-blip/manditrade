from __future__ import annotations

import streamlit as st

from modules.procurement.feed import render_procurement_feed


def render_procurement_dashboard(app_context: dict) -> None:
    st.subheader("Procurement Exchange")
    st.caption("Open requests, acceptance workflow, and advance-aware agreement creation.")
    render_procurement_feed(app_context)
