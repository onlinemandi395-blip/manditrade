from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_action_grid, render_metric_grid
from components.ui_shell import render_action_card, render_dual_panel, render_metric_card, render_page_header, render_showcase_strip


def render_actions_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("My Actions", "A single action inbox for approvals, RFQs, dispatch, payments, and worker follow-ups.", ["Action Center", "Role Aware"])
    if not user:
        st.info("Sign in to see pending actions.")
        return
    actions = app_context["action_center_service"].get_actions(user)
    if not actions:
        st.success("No pending actions right now.")
        return
    render_metric_grid(
        [
            render_metric_card("Pending Queues", str(len(actions)), "PENDING"),
            render_metric_card("Total Action Count", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
        ]
    )
    render_showcase_strip(
        [
            ("Priority Buckets", str(len(actions)), "PENDING"),
            ("Items Waiting", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
            ("Role", user.role.replace("_", " ").title(), "OPEN"),
        ]
    )
    render_section_intro("Role Inbox", "Use this panel to clear high-signal work first instead of scanning every module manually.")
    render_action_grid(
        [
            render_action_card(item["type"].replace("_", " ").title(), f"{item.get('count', 0)} pending items waiting for review or completion.", "Open module")
            for item in actions
        ]
    )
    render_dual_panel(
        "Action Strategy",
        "".join(
            [
                "<div class='mt-record__row'><span>Clear today</span><strong>High priority queues first</strong></div>",
                "<div class='mt-record__row'><span>Then</span><strong>Dispatch and payment follow-up</strong></div>",
            ]
        ),
        "Inbox Shape",
        "".join(
            f"<div class='mt-record__row'><span>{item['type'].replace('_', ' ').title()}</span><strong>{item.get('count', 0)}</strong></div>"
            for item in actions[:4]
        ),
    )
    st.dataframe(actions, use_container_width=True)
