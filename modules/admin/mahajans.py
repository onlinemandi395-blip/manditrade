from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state


def _format_mahajan_summary(mahajan: dict, supply_orders: list[dict]) -> dict:
    mahajan_id = mahajan.get("mahajan_id", "")
    linked_orders = [item for item in supply_orders if item.get("mahajan_id") == mahajan_id]
    open_orders = [item for item in linked_orders if item.get("status") not in {"CLOSED", "CANCELLED"}]
    return {
        "mahajan_id": mahajan_id,
        "business_name": mahajan.get("business_name", ""),
        "owner_name": mahajan.get("owner_name", ""),
        "email": mahajan.get("email", ""),
        "mobile": mahajan.get("mobile", ""),
        "city": mahajan.get("city", ""),
        "status": mahajan.get("status", "INVITED"),
        "linked_supply_orders": len(linked_orders),
        "open_supply_orders": len(open_orders),
        "created_at": mahajan.get("created_at", ""),
        "updated_at": mahajan.get("updated_at", ""),
    }


def render_mahajans_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]
    mahajans = governance_service.list_mahajans()
    supply_orders = procurement_service.list_supply_orders()
    pending_invites = [item for item in mahajans if item.get("status") == "INVITED"]
    active = [item for item in mahajans if item.get("status") == "ACTIVE"]
    summaries = [_format_mahajan_summary(item, supply_orders) for item in mahajans]

    render_page_header(
        "Mahajans",
        "Admin can onboard, review, update, and safely delete mahajan suppliers from this supply-control workspace.",
        ["Platform Admin", "Mahajan CRUD"],
    )
    render_metric_grid(
        [
            render_metric_card("Total Mahajans", str(len(mahajans)), "OPEN"),
            render_metric_card("Active Mahajans", str(len(active)), "SUCCESS"),
            render_metric_card("Pending Invites", str(len(pending_invites)), "PENDING"),
            render_metric_card("Open Supply Orders", str(len([item for item in supply_orders if item.get("status") not in {'CLOSED', 'CANCELLED'}])), "WARNING"),
        ]
    )
    overview_tab, registry_tab, create_tab, manage_tab = st.tabs(["Overview", "Registry", "Create", "Manage"])
    with overview_tab:
        render_section_intro("Mahajan Onboarding", "Mahajan is the admin-managed upstream supplier role. Manufacturers do not directly deal with mahajans.")
        if summaries:
            filtered_summaries = render_filter_bar(page_key="mahajan_overview", rows=summaries, search_fields=["mahajan_id", "business_name", "owner_name", "email"], status_field="status", date_field="updated_at")
            st.dataframe(filtered_summaries, use_container_width=True)
        else:
            render_empty_state("No mahajans registered yet.")
    with registry_tab:
        render_section_intro("Supplier Registry", "Track supplier master data along with linked mandi-order load before editing or deleting records.")
        if summaries:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(summaries), file_name="mahajans.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(summaries), file_name="mahajans.json", mime="application/json", use_container_width=True)
            st.dataframe(summaries, use_container_width=True)
        else:
            render_empty_state("No mahajan registry data available yet.")
    with create_tab:
        with st.form("create_mahajan"):
            mahajan_id = st.text_input("Mahajan ID", value=f"MAH{len(mahajans) + 1:03d}")
            business_name = st.text_input("Business Name")
            owner_name = st.text_input("Owner Name")
            email = st.text_input("Email")
            mobile = st.text_input("Mobile")
            city = st.text_input("City")
            notes = st.text_area("Notes")
            status = st.selectbox("Status", ["INVITED", "ACTIVE", "INACTIVE", "ARCHIVED"], index=0)
            submitted = st.form_submit_button("Create Mahajan")
        if submitted:
            try:
                governance_service.upsert_mahajan(
                    {
                        "mahajan_id": mahajan_id,
                        "business_name": business_name,
                        "owner_name": owner_name,
                        "email": email,
                        "mobile": mobile,
                        "city": city,
                        "notes": notes,
                        "status": status,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success("Mahajan created.")
                st.rerun()
    with manage_tab:
        if not mahajans:
            st.info("No mahajans registered yet.")
            return
        selected_id = st.selectbox(
            "Manage Mahajan",
            [item["mahajan_id"] for item in mahajans],
            format_func=lambda mahajan_id: f"{mahajan_id} | {next((item.get('business_name', '') for item in mahajans if item['mahajan_id'] == mahajan_id), '')}",
        )
        selected = next(item for item in mahajans if item["mahajan_id"] == selected_id)
        selected_summary = next(item for item in summaries if item["mahajan_id"] == selected_id)
        linked_orders = [item for item in supply_orders if item.get("mahajan_id") == selected_id]
        st.json(selected_summary, expanded=False)
        with st.form("manage_mahajan"):
            business_name = st.text_input("Business Name", value=selected.get("business_name", ""))
            owner_name = st.text_input("Owner Name", value=selected.get("owner_name", ""))
            email = st.text_input("Email", value=selected.get("email", ""))
            mobile = st.text_input("Mobile", value=selected.get("mobile", ""))
            city = st.text_input("City", value=selected.get("city", ""))
            notes = st.text_area("Notes", value=selected.get("notes", ""))
            status = st.selectbox(
                "Status",
                ["INVITED", "ACTIVE", "INACTIVE", "ARCHIVED"],
                index=["INVITED", "ACTIVE", "INACTIVE", "ARCHIVED"].index(selected.get("status", "INVITED")) if selected.get("status", "INVITED") in {"INVITED", "ACTIVE", "INACTIVE", "ARCHIVED"} else 0,
            )
            saved = st.form_submit_button("Update Mahajan")
        if saved:
            try:
                governance_service.upsert_mahajan(
                    {
                        "mahajan_id": selected_id,
                        "business_name": business_name,
                        "owner_name": owner_name,
                        "email": email,
                        "mobile": mobile,
                        "city": city,
                        "notes": notes,
                        "status": status,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success("Mahajan updated.")
                st.rerun()
        st.caption("Delete is blocked if this mahajan still owns raw materials or has open mandi supply orders.")
        if linked_orders:
            st.dataframe(linked_orders, use_container_width=True)
        delete_col, helper_col = st.columns([1, 2])
        with delete_col:
            if st.button("Delete Mahajan", use_container_width=True, key=f"delete_mahajan_{selected_id}"):
                try:
                    governance_service.delete_mahajan(selected_id)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.warning("Mahajan archived.")
                    st.rerun()
        with helper_col:
            st.info("Safe delete removes the supplier master record only after dependencies are cleared.")
