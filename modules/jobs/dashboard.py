from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state


def render_jobs_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    job_service = app_context["job_service"]
    worker_service = app_context["worker_service"]
    render_page_header("Jobs in Mandi", "Local labour network for mandi, factory, loading, packaging, and emergency shifts.", ["Jobs Network", "Responsive UI"])
    jobs = job_service.list_open_jobs()
    cards = [
        render_metric_card("Open Jobs", str(len(jobs)), "OPEN"),
        render_metric_card("Applications", str(len(job_service.list_applications())), "PENDING"),
        render_metric_card("Workers", str(len(worker_service.list_workers(include_private=True))), "SUCCESS"),
    ]
    render_metric_grid(cards)
    render_showcase_strip(
        [
            ("Daily Wage", "Fast local staffing", "OPEN"),
            ("Packaging", "Most active category", "SUCCESS"),
            ("Shift Help", "Urgent coverage lane", "WARNING"),
        ]
    )
    render_section_intro("Jobs Feed", "Manufacturers can post roles. Workers can apply with a simple note.")
    render_dual_panel(
        "Hiring Pulse",
        render_mobile_record_card({"Open Jobs": len(jobs), "Applications": len(job_service.list_applications())}),
        "Worker Pool",
        render_mobile_record_card({"Workers": len(worker_service.list_workers(include_private=True)), "Mode": "Local mandi network"}),
    )
    overview_tab, create_or_apply_tab, applications_tab = st.tabs(["Overview", "Create / Apply", "Applications"])

    with overview_tab:
        if jobs:
            filtered_jobs = render_filter_bar(page_key="jobs_overview", rows=jobs, search_fields=["job_id", "title", "manufacturer_id"], status_field="status", date_field="created_at", price_field="pay_amount", search_placeholder="Search by job ID or title")
            render_3d_panel("".join(render_mobile_record_card(item) for item in filtered_jobs[:5]), "Open Jobs Feed")
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_jobs), file_name="jobs.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_jobs), file_name="jobs.json", mime="application/json", use_container_width=True)
        else:
            render_empty_state("No open jobs are listed right now.")
    if user and user.role in {"manufacturer", "admin_as_manufacturer", "platform_admin"} and user.manufacturer_code:
        with create_or_apply_tab:
            with st.form("create_job_post"):
                col1, col2 = st.columns(2)
                title = col1.text_input("Title", value="Packaging Helper")
                work_type = col2.selectbox("Work Type", ["Full-time", "Part-time", "Daily Wage", "Shift-based", "Loading/unloading", "Packaging", "Machine operator", "Driver/helper", "Emergency labour"])
                worker_count = col1.number_input("Worker Count", min_value=1, step=1, value=3)
                city = col2.text_input("City", value="Pune")
                area = col1.text_input("Area", value="Bhosari")
                pay_type = col2.selectbox("Pay Type", ["daily", "shift", "monthly"])
                pay_amount = col1.number_input("Pay Amount", min_value=0.0, step=100.0, value=800.0)
                shift_time = col2.text_input("Shift Time", value="9AM-6PM")
                skills = st.text_input("Skills Required", value="Packaging,Loading")
                description = st.text_area("Description", value="Need urgent packaging workers for 2 days")
                submitted = st.form_submit_button("Post Job")
            if submitted:
                job_service.create_job(
                    manufacturer_id=user.manufacturer_code,
                    title=title,
                    work_type=work_type,
                    worker_count=int(worker_count),
                    city=city,
                    area=area,
                    pay_type=pay_type,
                    pay_amount=float(pay_amount),
                    shift_time=shift_time,
                    skills_required=[item.strip() for item in skills.split(",")],
                    description=description,
                    manufacturer_contact_email=user.email,
                )
                st.success("Job posted.")
                st.rerun()

            own_jobs = job_service.list_jobs(manufacturer_id=user.manufacturer_code)
            if own_jobs:
                render_3d_panel("".join(render_mobile_record_card(item) for item in own_jobs[:5]), "Your Active Jobs")

        with applications_tab:
            applications = job_service.list_applications(manufacturer_id=user.manufacturer_code)
            if applications:
                render_3d_panel("".join(render_mobile_record_card(item) for item in applications), "Applications Received")
                selected_application = st.selectbox("Manage Application", [item["application_id"] for item in applications])
                next_status = st.selectbox("Application Action", ["SHORTLISTED", "ACCEPTED", "REJECTED", "WORKER_CONFIRMED", "COMPLETED"])
                if st.button("Update Application Status", use_container_width=True):
                    selected = next(item for item in applications if item["application_id"] == selected_application)
                    job_service.update_application_status(job_id=selected["job_id"], application_id=selected_application, next_status=next_status)
                    st.success("Application updated.")
                    st.rerun()
            else:
                render_empty_state("No job applications have been received yet.")
    else:
        worker = worker_service.get_worker_by_email(user.email) if user else None
        with create_or_apply_tab:
            if worker:
                render_3d_panel("".join(render_mobile_record_card(item) for item in jobs), "Open Jobs Near Mandi")
                if jobs:
                    selected_job = st.selectbox("Apply To Job", [item["job_id"] for item in jobs])
                    note = st.text_area("Worker Note", value="Available from tomorrow morning")
                    if st.button("Apply", use_container_width=True):
                        job_service.apply_to_job(job_id=selected_job, worker_id=worker["worker_id"], worker_note=note, worker_contact_email=worker.get("linked_email", user.email))
                        st.success("Application submitted.")
                        st.rerun()
            else:
                render_empty_state("Create or enable a worker profile to apply for mandi jobs.")
        with applications_tab:
            if worker:
                worker_applications = job_service.list_applications(worker_id=worker["worker_id"])
                if worker_applications:
                    st.dataframe(worker_applications, use_container_width=True)
                else:
                    render_empty_state("No applications submitted yet.")
