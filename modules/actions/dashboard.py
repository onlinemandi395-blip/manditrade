from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_action_grid, render_metric_grid
from components.ui_shell import render_action_card, render_dual_panel, render_metric_card, render_page_header, render_showcase_strip
from utils.page_ui import get_active_filter, render_metric_button_row


def render_actions_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    page_key = "actions"
    render_page_header(
        "My Actions",
        "A single action inbox for approvals, RFQs, dispatch, payments, and worker follow-ups.",
        ["Action Center", "Role Aware"],
        role=user.role.replace("_", " ").title() if user else "Access Required",
        metrics=[("Priority View", "Operational first"), ("Signal Type", "Actionable queues")],
        kicker="Digital Manpur Command Surface",
    )
    if not user:
        st.info("Sign in to see pending actions.")
        return
    actions = app_context["action_center_service"].get_actions(user)
    total_count = sum(int(item.get("count", 0)) for item in actions)
    high_priority = sum(int(item.get("count", 0)) for item in actions[:2])
    render_metric_grid(
        [
            render_metric_card("Pending Queues", str(len(actions)), "PENDING"),
            render_metric_card("Total Action Count", str(total_count), "HIGH_PRIORITY"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Pending", "value": str(total_count), "tab_name": "Pending", "filter_value": "pending"},
            {"label": "High Priority", "value": str(high_priority), "tab_name": "High Priority", "filter_value": "high"},
            {"label": "Due Today", "value": str(total_count), "tab_name": "Due Today", "filter_value": "today"},
            {"label": "Completed", "value": "0", "tab_name": "Completed", "filter_value": "completed"},
        ],
    )
    render_showcase_strip(
        [
            ("Priority Buckets", str(len(actions)), "PENDING"),
            ("Items Waiting", str(total_count), "HIGH_PRIORITY"),
            ("Role", user.role.replace("_", " ").title(), "OPEN"),
        ]
    )
    render_section_intro("Role Inbox", "Use this panel to clear high-signal work first instead of scanning every module manually.")
    render_html(
        """
        <div class="mt-surface-note mt-command-glow">
          High-priority queues glow first by design here: overdue payments, unresolved proposals, RFQ replies,
          and dispatch bottlenecks should be cleared before lower-signal housekeeping.
        </div>
        """
    )
    pending_tab, priority_tab, today_tab, completed_tab = st.tabs(["Pending", "High Priority", "Due Today", "Completed"])
    active_filter = get_active_filter(page_key).lower()
    with pending_tab:
        if not actions:
            st.success("No pending actions right now.")
        else:
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
            if active_filter == "pending":
                st.caption("Metric filter applied: pending")
    with priority_tab:
        high_priority_rows = actions[:2] if actions else []
        if high_priority_rows:
            st.dataframe(high_priority_rows, use_container_width=True)
        else:
            st.info("No high-priority actions right now.")
    with today_tab:
        st.info("Role-safe due-today grouping is shown through the current pending queue until per-action due dates are added.")
        st.dataframe(actions, use_container_width=True)
    with completed_tab:
        st.info("Completed actions are not persisted separately yet.")
