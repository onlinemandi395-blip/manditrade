from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip


def render_admin_dashboard(app_context: dict) -> None:
    render_page_header("Platform Admin Dashboard", "Govern product approvals, manufacturer onboarding, and platform health without entering the old ERP agreement model.", ["Platform Admin", "Governance"])
    governance_service = app_context["governance_service"]
    products = governance_service.list_products()
    manufacturers = governance_service.list_manufacturers()
    actions = app_context["action_center_service"].get_actions(type("User", (), {"role": "platform_admin"})())
    pending_products = [item for item in products if item.get("status") == "PROPOSED"]
    active_products = [item for item in products if item.get("status") == "ACTIVE"]

    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(manufacturers)), "SUCCESS"),
            render_metric_card("Products", str(len(products)), "OPEN"),
            render_metric_card("Pending Actions", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
            render_metric_card("Approved Products", str(len(active_products)), "CONFIRMED"),
        ]
    )
    render_showcase_strip(
        [
            ("Product Queue", str(len(pending_products)), "PENDING"),
            ("Registry Health", str(len(manufacturers)), "SUCCESS"),
            ("Governance Load", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
        ]
    )
    render_dual_panel(
        "Approval Focus",
        render_mobile_record_card({"Pending Products": len(pending_products), "Active Products": len(active_products)}),
        "Registry Focus",
        render_mobile_record_card({"Manufacturers": len(manufacturers), "Actions": sum(int(item.get("count", 0)) for item in actions)}),
    )
    render_section_intro("Governance Overview", "Dashboard is now summary-only. Use Product Approvals for proposals and Manufacturers for registry controls plus onboarding packets.")
    st.dataframe(pending_products[:10], use_container_width=True)
    st.info("Manufacturer onboarding forms were removed from the dashboard. Open the Manufacturers page to create or manage onboarding packets.")
