from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header

SUBSCRIPTION_PLANS = ["Basic", "Premium", "Premium+"]


def _subscription_plan_index(value: str) -> int:
    normalized = (value or "").strip().lower()
    mapping = {
        "basic": "Basic",
        "premium": "Premium",
        "premium+": "Premium+",
    }
    display_value = mapping.get(normalized, value)
    return SUBSCRIPTION_PLANS.index(display_value) if display_value in SUBSCRIPTION_PLANS else 0


def render_manufacturers_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    onboarding_service = app_context["manufacturer_onboarding_service"]
    manufacturers = governance_service.list_manufacturers()

    render_page_header(
        "Manufacturers",
        "View the manufacturer registry and manage non-approval lifecycle states such as ACTIVE, INACTIVE, or BLOCKED.",
        ["Platform Admin", "Registry"],
    )
    render_metric_grid(
        [
            render_metric_card("Active", str(len([item for item in manufacturers if item.get("status") == "ACTIVE"])), "SUCCESS"),
            render_metric_card("Blocked", str(len([item for item in manufacturers if item.get("status") == "BLOCKED"])), "WARNING"),
            render_metric_card("Inactive", str(len([item for item in manufacturers if item.get("status") == "INACTIVE"])), "PENDING"),
        ]
    )
    render_section_intro("Registry", "Manufacturer onboarding does not require approval. Registry controls here are for maintenance and access control only.")
    st.dataframe(manufacturers, use_container_width=True)
    if not manufacturers:
        return

    selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers])
    selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
    col1, col2 = st.columns(2)
    updated_status = col1.selectbox("Lifecycle Status", ["ACTIVE", "INACTIVE", "BLOCKED"], index=["ACTIVE", "INACTIVE", "BLOCKED"].index(selected.get("status", "ACTIVE")) if selected.get("status", "ACTIVE") in {"ACTIVE", "INACTIVE", "BLOCKED"} else 0)
    updated_plan = col2.selectbox("Subscription Plan", SUBSCRIPTION_PLANS, index=_subscription_plan_index(selected.get("subscription_plan", "basic")))
    if st.button("Save Manufacturer Status", use_container_width=True):
        onboarding_service.update_manufacturer(
            selected_code,
            {
                "status": updated_status,
                "subscription_plan": updated_plan.strip(),
            },
        )
        st.success(f"{selected_code} updated.")
        st.rerun()
