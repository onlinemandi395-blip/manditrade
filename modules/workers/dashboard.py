from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_workers_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    worker_service = app_context["worker_service"]
    render_page_header("Workers", "Track available mandi workers, build worker profiles, and review public availability.", ["Workers", "3D Control"])
    workers = worker_service.list_workers(include_private=True)
    render_metric_grid(
        [
            render_metric_card("Worker Profiles", str(len(workers)), "SUCCESS"),
            render_metric_card("Public Workers", str(len(worker_service.list_workers())), "OPEN"),
        ]
    )
    overview_tab, profile_tab, pool_tab = st.tabs(["Overview", "My Worker Profile", "Worker Pool"])
    with overview_tab:
        render_section_intro("Worker Profiles", "Manufacturers can browse worker availability. Clients can opt into worker mode for local job discovery.")

    can_manage = bool(user and user.role in {"manufacturer", "admin_as_manufacturer", "platform_admin", "client", "worker"})
    with profile_tab:
        if can_manage and user:
            existing = worker_service.get_worker_by_email(user.email) or {}
            with st.form("worker_profile_form"):
                col1, col2 = st.columns(2)
                name = col1.text_input("Name", value=existing.get("name", user.name))
                mobile = col2.text_input("Mobile", value=existing.get("mobile", ""))
                city = col1.text_input("City", value=existing.get("city", "Pune"))
                area = col2.text_input("Area", value=existing.get("area", "Bhosari"))
                skills = st.text_input("Skills", value=",".join(existing.get("skills", ["Loading", "Packaging"])))
                preferred = st.text_input("Preferred Work Types", value=",".join(existing.get("preferred_work_type", ["Daily Wage", "Part-time"])))
                available = st.checkbox("Available", value=existing.get("available", True))
                public_opt_in = st.checkbox("Public Profile Opt-In", value=existing.get("public_profile_opt_in", True))
                submitted = st.form_submit_button("Save Worker Profile")
            if submitted:
                worker_service.upsert_worker(
                    linked_email=user.email,
                    name=name,
                    mobile=mobile,
                    city=city,
                    area=area,
                    skills=[item.strip() for item in skills.split(",")],
                    preferred_work_type=[item.strip() for item in preferred.split(",")],
                    available=available,
                    public_profile_opt_in=public_opt_in,
                )
                st.success("Worker profile saved.")
                st.rerun()

    public_workers = worker_service.list_workers()
    with pool_tab:
        if public_workers:
            render_3d_panel("".join(render_mobile_record_card(item) for item in public_workers), "Public Worker Pool")
        else:
            st.info("No public worker profiles are visible yet.")
