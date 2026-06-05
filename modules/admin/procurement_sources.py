from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.ui_shell import render_page_header


def render_procurement_sources_dashboard(app_context: dict) -> None:
    render_page_header(
        "Procurement Sources",
        "Navigation placeholder only. Procurement-source governance and source-domain modeling are intentionally deferred until the next phase.",
        ["Admin Placeholder", "Phase B Deferred"],
        role="Platform Admin",
        kicker="Source Governance Placeholder",
    )
    render_section_intro(
        "Phase Boundary",
        "No procurement-source business logic was added here. Use Orders, Warehouses, Shipments, and Admin Drive DB for the current operational flow.",
    )
    st.info("Procurement Sources will be activated in a later phase. This page exists only to complete the Phase A navigation model.")
