from __future__ import annotations

import streamlit as st

from components.actor_card import render_actor_card
from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from services.master_data_service import MasterDataService
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state

MAHAJAN_STATUSES = ["PENDING", "ACTIVE", "BLOCKED", "SUSPENDED", "ARCHIVED"]
MASTER_DATA = MasterDataService()


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _material_options() -> list[str]:
    return MASTER_DATA.get_raw_material_categories() + ["Yarn", "Fabric Inputs", "Packaging Material"]


def _state_options() -> list[str]:
    return MASTER_DATA.get_indian_states_and_union_territories()


def _render_mahajan_form(*, prefix: str, defaults: dict, submit_label: str) -> tuple[bool, dict]:
    address = defaults.get("address", {}) or {}
    banking = defaults.get("banking", {}) or {}
    material_options = _material_options()
    state_options = _state_options()

    with st.form(f"{prefix}_mahajan_admin_form"):
        id_col, status_col = st.columns(2)
        mahajan_id = id_col.text_input("Mahajan ID", value=defaults.get("mahajan_id", ""))
        status = status_col.selectbox("Lifecycle Status", MAHAJAN_STATUSES, index=_option_index(MAHAJAN_STATUSES, defaults.get("status", "PENDING")))

        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business Name", value=defaults.get("business_name", ""))
        owner_name = col2.text_input("Contact Person", value=defaults.get("owner_name", ""))
        email = col1.text_input("Email", value=defaults.get("email", ""))
        mobile = col2.text_input("Phone", value=defaults.get("mobile", ""))
        city = col1.text_input("City", value=defaults.get("city", ""))
        coverage_area = col2.text_input("Coverage Area", value=defaults.get("coverage_area", ""))

        raw_material_categories = st.multiselect(
            "Raw Material Categories",
            material_options,
            default=[item for item in (defaults.get("raw_material_categories", []) or []) if item in set(material_options)],
        )
        states_served = st.multiselect(
            "States Served",
            state_options,
            default=[item for item in (defaults.get("states_served", []) or []) if item in set(state_options)],
        )

        moq_col, rating_col = st.columns(2)
        minimum_order_qty = moq_col.number_input("MOQ", min_value=0.0, value=float(defaults.get("minimum_order_qty", 0) or 0), step=1.0)
        rating = rating_col.number_input("Rating", min_value=0.0, max_value=5.0, value=float(defaults.get("rating", 0) or 0), step=0.5)

        st.markdown("#### Address")
        address_line1 = st.text_input("Address Line 1", value=address.get("line1", ""))
        address_line2 = st.text_input("Address Line 2", value=address.get("line2", ""))
        state = st.selectbox("State", state_options, index=_option_index(state_options, address.get("state", "")))
        pin_code = st.text_input("Pincode", value=address.get("pin_code", ""))

        st.markdown("#### Banking")
        bank_col1, bank_col2 = st.columns(2)
        account_holder_name = bank_col1.text_input("Account Holder", value=banking.get("account_holder_name", ""))
        account_number = bank_col2.text_input("Account Number", value=banking.get("account_number", ""))
        ifsc = bank_col1.text_input("IFSC", value=banking.get("ifsc", ""))
        upi_id = bank_col2.text_input("UPI", value=banking.get("upi_id", ""))

        notes = st.text_area("Notes", value=defaults.get("notes", ""), height=100)
        submitted = st.form_submit_button(submit_label)

    payload = {
        "mahajan_id": mahajan_id.strip().upper(),
        "business_name": business_name.strip(),
        "owner_name": owner_name.strip(),
        "email": email.strip().lower(),
        "mobile": mobile.strip(),
        "city": city.strip(),
        "coverage_area": coverage_area.strip(),
        "states_served": states_served,
        "raw_material_categories": raw_material_categories,
        "minimum_order_qty": float(minimum_order_qty or 0),
        "rating": float(rating or 0),
        "status": status.strip(),
        "address": {
            "line1": address_line1.strip(),
            "line2": address_line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
        },
        "banking": {
            "account_holder_name": account_holder_name.strip(),
            "account_number": account_number.strip(),
            "ifsc": ifsc.strip(),
            "upi_id": upi_id.strip(),
        },
        "notes": notes.strip(),
    }
    return submitted, payload


def _render_directory(rows: list[dict], *, section_key: str) -> None:
    if not rows:
        render_empty_state("No mahajan directory records available.")
        return
    for index in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, row in zip(columns, rows[index:index + 3]):
            with column:
                selected = render_actor_card(
                    actor_id=row.get("mahajan_id", ""),
                    title=row.get("business_name", ""),
                    subtitle=row.get("owner_name", ""),
                    status=row.get("status", "PENDING"),
                    completion_score=row.get("completion_score", 0),
                    trust_tier=row.get("trust_tier", "Bronze"),
                    location=row.get("location", ""),
                    supporting_text=", ".join(row.get("raw_material_categories", [])[:2]),
                    badges=(row.get("verification_badges", []) + row.get("trust_badges", []))[:4],
                    action_label="Select",
                    action_key=f"{section_key}_{row.get('mahajan_id', '')}",
                )
                if selected:
                    st.session_state["manage_mahajan_record"] = row.get("mahajan_id", "")


def render_mahajans_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    access_portal_service = app_context["access_portal_service"]
    identity_service = app_context["identity_governance_service"]
    mahajans = governance_service.list_mahajans()
    summaries = [identity_service.summarize_mahajan(item) for item in mahajans]
    counts = identity_service.readiness_counts("mahajan", mahajans)

    render_page_header(
        "Mahajans",
        "Admin governs mahajan supplier identity, sourcing coverage, verification readiness, and activation.",
        ["Platform Admin", "Supplier Governance"],
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
        render_section_intro("Mahajan Governance", "Mahajans stay admin-routed. Identity strength now feeds later supply trust and sourcing quality surfaces.")
        if summaries:
            st.dataframe(summaries, use_container_width=True)
        else:
            render_empty_state("No mahajans registered yet.")

    with directory_tab:
        filtered = render_filter_bar(
            page_key="mahajan_directory",
            rows=summaries,
            search_fields=["mahajan_id", "business_name", "owner_name", "email", "city", "coverage_area"],
            status_field="status",
            date_field="updated_at",
            search_placeholder="Search mahajan, supplier contact, coverage, or city",
        )
        if filtered:
            _render_directory(filtered, section_key="mahajan_directory")
            st.dataframe(filtered, use_container_width=True)
        else:
            render_empty_state("No mahajans match the current filter.")

    with pending_tab:
        rows = [row for row in summaries if row.get("status") == "PENDING"]
        if rows:
            _render_directory(rows, section_key="mahajan_pending")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No pending mahajan approvals.")

    with active_tab:
        rows = [row for row in summaries if row.get("status") == "ACTIVE"]
        if rows:
            _render_directory(rows, section_key="mahajan_active")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No active mahajans found.")

    with blocked_tab:
        rows = [row for row in summaries if row.get("status") in {"BLOCKED", "SUSPENDED"}]
        if rows:
            _render_directory(rows, section_key="mahajan_blocked")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No blocked mahajans found.")

    with archived_tab:
        rows = [row for row in summaries if row.get("status") == "ARCHIVED"]
        if rows:
            _render_directory(rows, section_key="mahajan_archived")
            st.dataframe(rows, use_container_width=True)
        else:
            render_empty_state("No archived mahajans found.")

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
                        "mahajan_id": row.get("mahajan_id", ""),
                        "business_name": row.get("business_name", ""),
                        "completion_score": row.get("completion_score", 0),
                        "trust_tier": row.get("trust_tier", "Bronze"),
                        "status": row.get("status", "PENDING"),
                    }
                    for row in summaries
                ],
                use_container_width=True,
            )
        else:
            render_empty_state("No mahajan analytics available yet.")

    with create_tab:
        defaults = {"mahajan_id": f"MAH{len(mahajans) + 1:03d}", "status": "PENDING"}
        submitted, payload = _render_mahajan_form(prefix="mahajan_create", defaults=defaults, submit_label="Create Mahajan Invitation")
        if submitted:
            try:
                saved = governance_service.upsert_mahajan(payload)
                access_portal_service.submit_signup_request(
                    requested_role="mahajan",
                    email=saved["email"],
                    full_name=saved.get("owner_name", ""),
                    city=saved.get("city", ""),
                    mobile=saved.get("mobile", ""),
                    business_name=saved.get("business_name", ""),
                    note="Admin-created mahajan invitation",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success(f"Mahajan {saved['mahajan_id']} invited.")
                st.rerun()

    with manage_tab:
        if not mahajans:
            st.info("No mahajans available to manage yet.")
        else:
            selected_id = st.selectbox("Manage Mahajan", [item["mahajan_id"] for item in mahajans], key="manage_mahajan_record")
            selected = next(item for item in mahajans if item["mahajan_id"] == selected_id)
            st.json(identity_service.summarize_mahajan(selected), expanded=False)
            submitted, payload = _render_mahajan_form(prefix=f"mahajan_manage_{selected_id}", defaults=selected, submit_label="Save Mahajan")
            if submitted:
                try:
                    governance_service.upsert_mahajan(payload)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success(f"{selected_id} updated.")
                    st.rerun()
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            if action_col1.button("Approve", key=f"approve_mah_{selected_id}", use_container_width=True):
                governance_service.upsert_mahajan({**selected, "status": "ACTIVE"})
                st.success(f"{selected_id} approved.")
                st.rerun()
            if action_col2.button("Block", key=f"block_mah_{selected_id}", use_container_width=True):
                governance_service.upsert_mahajan({**selected, "status": "BLOCKED"})
                st.warning(f"{selected_id} blocked.")
                st.rerun()
            if action_col3.button("Suspend", key=f"suspend_mah_{selected_id}", use_container_width=True):
                governance_service.upsert_mahajan({**selected, "status": "SUSPENDED"})
                st.warning(f"{selected_id} suspended.")
                st.rerun()
            if action_col4.button("Archive", key=f"archive_mah_{selected_id}", use_container_width=True):
                governance_service.upsert_mahajan({**selected, "status": "ARCHIVED"})
                st.warning(f"{selected_id} archived.")
                st.rerun()

    if summaries:
        st.download_button(
            "Export Mahajan Directory JSON",
            export_rows_to_json_bytes(summaries),
            file_name="mahajan_directory.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Export Mahajan Directory CSV",
            export_rows_to_csv_bytes(summaries),
            file_name="mahajan_directory.csv",
            mime="text/csv",
            use_container_width=True,
        )
