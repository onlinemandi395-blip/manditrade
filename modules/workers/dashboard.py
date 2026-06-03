from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip
from utils.page_ui import render_metric_button_row


def render_workers_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    worker_service = app_context["worker_service"]
    job_service = app_context["job_service"]

    render_page_header(
        "Worker Dashboard",
        "Read-only view for worker profile status, open jobs, applications, and current work pipeline.",
        ["Read Only", "Jobs Network"],
    )

    worker_record = worker_service.get_worker_by_email(user.email) if user else {}
    worker_id = worker_record.get("worker_id", "")
    public_workers = worker_service.list_workers()
    open_jobs = job_service.list_open_jobs()
    worker_applications = job_service.list_applications(worker_id=worker_id) if worker_id else []
    active_applications = [item for item in worker_applications if item.get("status") not in {"REJECTED", "COMPLETED"}]

    render_metric_grid(
        [
            render_metric_card("Profile Status", "Linked" if worker_record else "Pending", "SUCCESS" if worker_record else "PENDING"),
            render_metric_card("Open Jobs", str(len(open_jobs)), "OPEN"),
            render_metric_card("My Applications", str(len(worker_applications)), "WARNING"),
            render_metric_card("Public Worker Pool", str(len(public_workers)), "SUCCESS"),
        ]
    )
    render_showcase_strip(
        [
            ("Available", str(bool(worker_record.get("available", False))) if worker_record else "False", "OPEN"),
            ("Public Profile", str(bool(worker_record.get("public_profile_opt_in", False))) if worker_record else "False", "SUCCESS"),
            ("Active Applications", str(len(active_applications)), "PENDING"),
        ]
    )
    render_metric_button_row(
        "worker_dashboard",
        [
            {"label": "Overview", "value": str(len(open_jobs)), "tab_name": "Overview"},
            {"label": "Open Jobs", "value": str(len(open_jobs)), "tab_name": "Open Jobs"},
            {"label": "Applications", "value": str(len(worker_applications)), "tab_name": "Applications"},
        ],
    )
    render_section_intro(
        "Read-Only Work View",
        "This dashboard is summary-only. Use Jobs and My Profile pages to apply, update profile details, or manage work activity.",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Job Pipeline")
        st.bar_chart(
            {
                "Open Jobs": len(open_jobs),
                "My Applications": len(worker_applications),
                "Active Applications": len(active_applications),
            }
        )
    with col2:
        st.markdown("#### Profile Snapshot")
        st.bar_chart(
            {
                "Available": 1 if worker_record.get("available", False) else 0,
                "Public Profile": 1 if worker_record.get("public_profile_opt_in", False) else 0,
                "Skills": len(worker_record.get("skills", []) or []),
            }
        )

    overview_tab, jobs_tab, applications_tab = st.tabs(["Overview", "Open Jobs", "Applications"])
    with overview_tab:
        st.dataframe(
            [
                {
                    "worker_id": worker_record.get("worker_id", ""),
                    "name": worker_record.get("name", user.name),
                    "city": worker_record.get("city", ""),
                    "area": worker_record.get("area", ""),
                    "available": worker_record.get("available", False),
                    "public_profile_opt_in": worker_record.get("public_profile_opt_in", False),
                }
            ],
            use_container_width=True,
        )
    with jobs_tab:
        st.dataframe(open_jobs, use_container_width=True)
    with applications_tab:
        st.dataframe(worker_applications, use_container_width=True)
