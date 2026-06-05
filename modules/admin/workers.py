from __future__ import annotations

import streamlit as st

from components.actor_card import render_actor_card
from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state

WORKER_STATUSES = ["PENDING", "ACTIVE", "BLOCKED", "SUSPENDED", "ARCHIVED"]
WORK_TYPES = [
    "Full-time",
    "Part-time",
    "Daily Wage",
    "Shift-based",
    "Packaging",
    "Machine Operator",
    "Driver",
    "Loader",
]


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _render_worker_form(*, prefix: str, defaults: dict, submit_label: str) -> tuple[bool, dict]:
    skills_default = ", ".join(defaults.get("skills", []) or [])
    selected_types = [item for item in (defaults.get("preferred_work_type", []) or []) if item in set(WORK_TYPES)]
    with st.form(f"{prefix}_worker_admin_form"):
        id_col, status_col = st.columns(2)
        worker_id = id_col.text_input("Worker ID", value=defaults.get("worker_id", ""), disabled=bool(defaults.get("worker_id")))
        status = status_col.selectbox("Lifecycle Status", WORKER_STATUSES, index=_option_index(WORKER_STATUSES, defaults.get("status", "PENDING")))
        col1, col2 = st.columns(2)
        name = col1.text_input("Worker Name", value=defaults.get("name", ""))
        linked_email = col2.text_input("Email", value=defaults.get("linked_email", ""))
        mobile = col1.text_input("Phone", value=defaults.get("mobile", ""))
        city = col2.text_input("City", value=defaults.get("city", ""))
        area = col1.text_input("Area", value=defaults.get("area", ""))
        state = col2.text_input("State", value=defaults.get("state", ""))
        skills = st.text_input("Skills", value=skills_default, help="Comma-separated skills")
        preferred_work_type = st.multiselect("Preferred Work Type", WORK_TYPES, default=selected_types)
        rate_col1, rate_col2 = st.columns(2)
        daily_rate = rate_col1.number_input("Daily Rate", min_value=0.0, value=float(defaults.get("daily_rate", 0) or 0), step=50.0)
        monthly_rate = rate_col2.number_input("Monthly Rate", min_value=0.0, value=float(defaults.get("monthly_rate", 0) or 0), step=500.0)
        available = st.checkbox("Available", value=bool(defaults.get("available", True)))
        public_profile_opt_in = st.checkbox("Show in worker directory", value=bool(defaults.get("public_profile_opt_in", False)))
        notes = st.text_area("Notes", value=defaults.get("notes", ""), height=100)
        submitted = st.form_submit_button(submit_label)

    payload = {
        "worker_id": defaults.get("worker_id", ""),
        "linked_email": linked_email.strip().lower(),
        "name": name.strip(),
        "mobile": mobile.strip(),
        "city": city.strip(),
        "area": area.strip(),
        "state": state.strip(),
        "skills": [item.strip() for item in skills.split(",") if item.strip()],
        "preferred_work_type": preferred_work_type,
        "available": available,
        "availability_status": "AVAILABLE" if available else "BUSY",
        "daily_rate": float(daily_rate or 0),
        "monthly_rate": float(monthly_rate or 0),
        "status": status.strip(),
        "public_profile_opt_in": public_profile_opt_in,
        "notes": notes.strip(),
    }
    return submitted, payload


def _render_worker_cards(rows: list[dict], *, section_key: str) -> None:
    if not rows:
        render_empty_state("No worker records available.")
        return
    for index in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, row in zip(columns, rows[index:index + 3]):
            with column:
                selected = render_actor_card(
                    actor_id=row.get("worker_id", ""),
                    title=row.get("name", ""),
                    subtitle=", ".join(row.get("skills", [])[:2]) or "Worker",
                    status=row.get("status", "PENDING"),
                    completion_score=row.get("completion_score", 0),
                    trust_tier=row.get("trust_tier", "Bronze"),
                    location=row.get("location", ""),
                    supporting_text=f"Daily Rate: INR {row.get('daily_rate', 0):.0f}",
                    badges=(row.get("verification_badges", []) + row.get("trust_badges", []))[:4],
                    action_label="Select",
                    action_key=f"{section_key}_{row.get('worker_id', '')}",
                )
                if selected:
                    st.session_state["manage_worker_record"] = row.get("linked_email", "")


def render_workers_admin_dashboard(app_context: dict) -> None:
    worker_service = app_context["worker_service"]
    access_portal_service = app_context["access_portal_service"]
    identity_service = app_context["identity_governance_service"]

    workers = worker_service.list_workers(include_private=True)
    summaries = [identity_service.summarize_worker(item) for item in workers]
    counts = identity_service.readiness_counts("worker", workers)

    render_page_header(
        "Workers",
        "Admin controls worker identity, skill readiness, availability visibility, and approval status from one governance workspace.",
        ["Platform Admin", "Worker Governance"],
    )
    render_metric_grid(
        [
            render_metric_card("Pending Approvals", str(counts["pending"]), "PENDING"),
            render_metric_card("Active", str(counts["active"]), "SUCCESS"),
            render_metric_card("Blocked / Suspended", str(counts["blocked"]), "WARNING"),
            render_metric_card("Trusted", str(counts["trusted"]), "OPEN"),
        ]
    )

    tabs = st.tabs(["Overview", "Directory", "Pending Approvals", "Active", "Blocked", "Archived", "Analytics", "Create", "Manage"])
    overview_tab, directory_tab, pending_tab, active_tab, blocked_tab, archived_tab, analytics_tab, create_tab, manage_tab = tabs

    with overview_tab:
        render_section_intro("Worker Governance", "Workers should sign in, complete profile basics, and wait for admin approval before operational activation.")
        if summaries:
            st.dataframe(summaries, use_container_width=True)
        else:
            render_empty_state("No workers registered yet.")

    with directory_tab:
        filtered = render_filter_bar(
            page_key="worker_directory",
            rows=summaries,
            search_fields=["worker_id", "name", "linked_email", "city", "area", "state"],
            status_field="status",
            date_field="updated_at",
            search_placeholder="Search worker, email, city, area, or skill",
        )
        if filtered:
            _render_worker_cards(filtered, section_key="worker_directory")
            st.dataframe(filtered, use_container_width=True)
        else:
            render_empty_state("No workers match the current filter.")

    with pending_tab:
        rows = [row for row in summaries if row.get("status") == "PENDING"]
        if rows:
            _render_worker_cards(rows, section_key="worker_pending")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No pending workers.")

    with active_tab:
        rows = [row for row in summaries if row.get("status") == "ACTIVE"]
        if rows:
            _render_worker_cards(rows, section_key="worker_active")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No active workers.")

    with blocked_tab:
        rows = [row for row in summaries if row.get("status") in {"BLOCKED", "SUSPENDED"}]
        if rows:
            _render_worker_cards(rows, section_key="worker_blocked")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No blocked workers.")

    with archived_tab:
        rows = [row for row in summaries if row.get("status") == "ARCHIVED"]
        if rows:
            _render_worker_cards(rows, section_key="worker_archived")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No archived workers.")

    with analytics_tab:
        if summaries:
            st.bar_chart(
                {
                    "Pending": counts["pending"],
                    "Active": counts["active"],
                    "Blocked": counts["blocked"],
                    "Trusted": counts["trusted"],
                }
            )
            st.dataframe(
                [
                    {
                        "worker_id": row.get("worker_id", ""),
                        "name": row.get("name", ""),
                        "completion_score": row.get("completion_score", 0),
                        "trust_tier": row.get("trust_tier", "Bronze"),
                        "status": row.get("status", "PENDING"),
                    }
                    for row in summaries
                ],
                use_container_width=True,
            )
        else:
            render_empty_state("No worker analytics available.")

    with create_tab:
        submitted, payload = _render_worker_form(prefix="worker_create", defaults={"status": "PENDING"}, submit_label="Create Worker Invitation")
        if submitted:
            try:
                saved = worker_service.upsert_worker(**payload)
                access_portal_service.submit_signup_request(
                    requested_role="worker",
                    email=saved["linked_email"],
                    full_name=saved.get("name", ""),
                    city=saved.get("city", ""),
                    mobile=saved.get("mobile", ""),
                    area=saved.get("area", ""),
                    skills=saved.get("skills", []),
                    preferred_work_type=saved.get("preferred_work_type", []),
                    note="Admin-created worker invitation",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success(f"Worker {saved['worker_id']} invited.")
                st.rerun()

    with manage_tab:
        if not workers:
            st.info("No workers available to manage yet.")
        else:
            worker_options = [item["linked_email"] for item in workers]
            selected_email = st.selectbox("Manage Worker", worker_options, key="manage_worker_record")
            selected = next(item for item in workers if item["linked_email"] == selected_email)
            st.json(identity_service.summarize_worker(selected), expanded=False)
            submitted, payload = _render_worker_form(prefix=f"worker_manage_{selected.get('worker_id', '')}", defaults=selected, submit_label="Save Worker")
            if submitted:
                try:
                    worker_service.upsert_worker(**payload)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success(f"{selected.get('worker_id', '')} updated.")
                    st.rerun()
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            update_base = {
                "linked_email": selected.get("linked_email", ""),
                "name": selected.get("name", ""),
                "mobile": selected.get("mobile", ""),
                "city": selected.get("city", ""),
                "area": selected.get("area", ""),
                "state": selected.get("state", ""),
                "skills": selected.get("skills", []),
                "preferred_work_type": selected.get("preferred_work_type", []),
                "available": selected.get("available", True),
                "availability_status": selected.get("availability_status", "AVAILABLE"),
                "daily_rate": selected.get("daily_rate", 0),
                "monthly_rate": selected.get("monthly_rate", 0),
                "public_profile_opt_in": selected.get("public_profile_opt_in", False),
                "notes": selected.get("notes", ""),
            }
            if action_col1.button("Approve", key=f"approve_worker_{selected.get('worker_id', '')}", use_container_width=True):
                worker_service.upsert_worker(**update_base, status="ACTIVE")
                st.success("Worker approved.")
                st.rerun()
            if action_col2.button("Block", key=f"block_worker_{selected.get('worker_id', '')}", use_container_width=True):
                worker_service.upsert_worker(**update_base, status="BLOCKED")
                st.warning("Worker blocked.")
                st.rerun()
            if action_col3.button("Suspend", key=f"suspend_worker_{selected.get('worker_id', '')}", use_container_width=True):
                worker_service.upsert_worker(**update_base, status="SUSPENDED")
                st.warning("Worker suspended.")
                st.rerun()
            if action_col4.button("Archive", key=f"archive_worker_{selected.get('worker_id', '')}", use_container_width=True):
                worker_service.upsert_worker(**update_base, status="ARCHIVED")
                st.warning("Worker archived.")
                st.rerun()

    if summaries:
        st.download_button(
            "Export Worker Directory JSON",
            export_rows_to_json_bytes(summaries),
            file_name="worker_directory.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Export Worker Directory CSV",
            export_rows_to_csv_bytes(summaries),
            file_name="worker_directory.csv",
            mime="text/csv",
            use_container_width=True,
        )
