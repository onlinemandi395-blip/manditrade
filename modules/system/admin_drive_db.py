from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.data_grid import render_data_grid
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.toast_manager import push_toast
from components.ui_shell import render_metric_card, render_page_header
from services.navigation_service import get_navigation_runtime_info


def _create_smoke_record(app_context: dict) -> dict:
    return app_context["admin_drive_database_service"].create_smoke_record()


def render_admin_drive_db_dashboard(app_context: dict) -> None:
    service = app_context["admin_drive_database_service"]
    render_page_header(
        "Admin Drive DB",
        "Inspect the configured Admin Drive database root, validate canonical structure, and run safe bootstrap and smoke actions from one page.",
        ["Admin Drive", "Canonical Storage", "Visibility"],
        role="Platform Admin",
        metrics=[
            ("Drive Mode", app_context["drive_service"].describe_runtime_mode()),
            ("Storage Mode", app_context["system_config"]["storage"].get("mode", "compatibility")),
            ("Backend", service.runtime_status().get("runtime_backend", "local_path_mirror")),
        ],
        kicker="Admin Storage Control",
    )
    root = service.resolve_root_config()
    latest_validation = service.load_latest_validation_report()
    latest_bootstrap = service.load_latest_bootstrap_report()
    latest_structure = service._read_report(service.reports_dir / "latest_admin_drive_db_structure.json")
    validation = latest_validation or service.validate_database_tree(persist=False)
    tree_status = service.get_database_tree_status()
    service_account = tree_status.get("service_account", {})
    runtime = validation.get("runtime", root)
    nav_info = get_navigation_runtime_info("platform_admin", app_context)
    canonical_readiness = "READY" if validation.get("status") == "PASS" and not validation.get("critical_errors") else "NOT READY"
    if latest_bootstrap.get("status") in {"FAILED", "PARTIAL"} or tree_status.get("missing"):
        recommended_next_action = "Bootstrap Missing Folders"
    elif validation.get("status") != "PASS":
        recommended_next_action = "Validate DB"
    else:
        recommended_next_action = "Create Smoke Record"
    render_metric_grid(
        [
            render_metric_card("Drive Mode", "Service Account" if tree_status.get("mode") == "GOOGLE_DRIVE" else "Local Mirror", "SUCCESS" if tree_status.get("mode") == "GOOGLE_DRIVE" else "OPEN"),
            render_metric_card("Root Folder", root.get("root_folder_name", "MANDITRADE_DB") or "MANDITRADE_DB", "SUCCESS"),
            render_metric_card("Connection", "Connected" if runtime.get("drive_api_ready", False) else "Not Connected", "SUCCESS" if runtime.get("drive_api_ready", False) else "WARNING"),
            render_metric_card("Validation", validation.get("status", "UNKNOWN"), "SUCCESS" if validation.get("status") == "PASS" else "WARNING"),
        ]
    )
    render_section_intro("Connection Status", "Use this page to confirm whether Admin Drive is truly connected or whether the app is currently using the local canonical mirror.")
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.write(f"Drive Mode: {'Service Account' if tree_status.get('mode') == 'GOOGLE_DRIVE' else 'Local Mirror'}")
        st.write(f"Root Folder: {root.get('root_folder_name', 'MANDITRADE_DB') or 'MANDITRADE_DB'}")
        st.write(f"Root Folder ID: {root.get('root_folder_id', '') or 'Not available'}")
        st.write(f"Credential Source: {service_account.get('source', 'MISSING')}")
        st.write(f"Service Account Email: {service_account.get('client_email', '') or 'Not available'}")
    with status_col2:
        st.write(f"Connection: {'Connected' if runtime.get('drive_api_ready', False) else 'Not Connected'}")
        st.write(f"Last Checked: {tree_status.get('last_checked', '')}")
        st.write(f"Bootstrap Status: {latest_bootstrap.get('status', 'MISSING')}")
        st.write(f"Validation Status: {validation.get('status', 'UNKNOWN')}")
        st.write(f"Recommended Next Action: {recommended_next_action}")
    if runtime.get("drive_api_ready", False):
        st.success("Google Drive is connected through the configured service account, and Admin Drive DB metadata is being read live.")
    else:
        st.warning("Google Drive is not connected. The app is using local mirror fallback.")
        if runtime.get("reason"):
            st.caption(f"Runtime detail: {runtime.get('reason')}")
        missing_items = []
        if not service_account.get("configured"):
            missing_items.append("Missing GOOGLE_SERVICE_ACCOUNT_JSON or [google_drive].service_account_json")
        if not root.get("root_folder_id"):
            missing_items.append("Missing ADMIN_DRIVE_ROOT_FOLDER_ID or [google_drive].admin_db_root_folder_id")
        if missing_items:
            st.info("Missing setup: " + " | ".join(missing_items))
        st.info(
            "Drive DB uses a Google Service Account. Add `[google_drive].service_account_json`, "
            "`[google_drive].admin_db_root_folder_name`, and `[google_drive].admin_db_root_folder_id` in `.streamlit/secrets.toml`, "
            "then share the Drive folder with the service account email as Editor."
        )

    render_section_intro("Actions", "Use these actions to inspect, bootstrap, validate, and smoke-test the canonical Admin Drive root. No action auto-switches storage mode.")
    col1, col2, col3, col4, col5 = st.columns(5)
    if col1.button("Validate Admin Drive DB", use_container_width=True):
        report = service.validate_database_tree(persist=True)
        push_toast(f"Validation finished with status {report.get('status', 'UNKNOWN')}.", tone="success", title="Admin Drive DB")
        st.rerun()
    if col2.button("Bootstrap Dry Run", use_container_width=True):
        report = service.bootstrap(dry_run=True)
        push_toast(f"Bootstrap dry run finished with recommendation {report.get('recommendation', 'UNKNOWN')}.", tone="info", title="Admin Drive DB")
        st.rerun()
    if col3.button("Bootstrap Execute if Safe", use_container_width=True):
        report = service.bootstrap(dry_run=False)
        push_toast(f"Bootstrap execute finished with recommendation {report.get('recommendation', 'UNKNOWN')}.", tone="success", title="Admin Drive DB")
        st.rerun()
    if col4.button("Create Smoke Record", use_container_width=True):
        smoke = _create_smoke_record(app_context)
        st.session_state["admin_drive_db_smoke_result"] = smoke
        push_toast(f"Smoke record written to {Path(smoke['path']).name}.", tone="success", title="Admin Drive DB")
        st.rerun()
    if col5.button("Refresh", use_container_width=True):
        st.rerun()

    extra_col1, extra_col2 = st.columns(2)
    if extra_col1.button("Bootstrap Missing Folders", use_container_width=True):
        report = service.bootstrap(dry_run=False)
        push_toast(f"Missing folders/bootstrap ensured with recommendation {report.get('recommendation', 'UNKNOWN')}.", tone="success", title="Admin Drive DB")
        st.rerun()
    if extra_col2.button("Open Root Folder", use_container_width=True):
        if tree_status.get("mode") == "GOOGLE_DRIVE" and root.get("root_folder_id"):
            st.session_state["admin_drive_db_root_hint"] = f"https://drive.google.com/drive/folders/{root.get('root_folder_id')}"
        else:
            st.session_state["admin_drive_db_root_hint"] = tree_status.get("root", {}).get("path", root.get("root_path", ""))
        st.rerun()

    root_hint = st.session_state.get("admin_drive_db_root_hint", "")
    if root_hint:
        st.info(f"Open Root Folder target: {root_hint}")

    render_section_intro("Live Drive Explorer", "See the required Admin Drive DB tree, key files, and whether each entry exists in live Google Drive metadata or the local canonical mirror.")
    explorer_rows = [
        {
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "logical_path": item.get("logical_path", ""),
            "id": item.get("id", ""),
            "path": item.get("path", ""),
            "record_count": item.get("record_count"),
            "last_modified": item.get("last_modified", ""),
            "status": item.get("status", "UNKNOWN"),
        }
        for item in tree_status.get("items", [])
    ]
    render_data_grid(
        page_key="admin_drive_db_explorer",
        rows=explorer_rows,
        search_fields=["name", "logical_path", "path", "status", "type"],
        status_field="status",
        search_placeholder="Search folders and files",
    )

    if tree_status.get("missing"):
        st.warning("Missing entries: " + ", ".join(tree_status.get("missing", [])))
    if tree_status.get("warnings"):
        st.info("Warnings: " + " | ".join(tree_status.get("warnings", [])))

    st.markdown("### Bootstrap Report")
    bootstrap_view = {
        "status": latest_bootstrap.get("status", "MISSING"),
        "folders_created": latest_bootstrap.get("folders_created", 0),
        "files_created": latest_bootstrap.get("files_created", 0),
        "already_existing": latest_bootstrap.get("already_existing", {}),
        "errors": latest_bootstrap.get("errors", []),
        "timestamp": latest_bootstrap.get("generated_at", ""),
    }
    st.json(bootstrap_view, expanded=False)

    st.markdown("### Navigation Inspector")
    st.json(
        {
            "active_role": nav_info.get("active_role", "platform_admin"),
            "default_route": nav_info.get("default_route", ""),
            "source_used": nav_info.get("source", "UNKNOWN"),
            "config_path": nav_info.get("path", ""),
            "loaded_roles": nav_info.get("loaded_roles", []),
            "loaded_at": nav_info.get("loaded_at", ""),
            "nav_item_count": nav_info.get("nav_item_count", 0),
            "nav_groups": nav_info.get("nav_groups", []),
            "config_errors": nav_info.get("errors", []),
            "warnings": nav_info.get("warnings", []),
            "service_account_email": service_account.get("client_email", ""),
        },
        expanded=False,
    )
    smoke_result = st.session_state.get("admin_drive_db_smoke_result")
    if smoke_result:
        st.markdown("### Smoke Record Result")
        if smoke_result.get("success"):
            st.success(smoke_result.get("message", "Smoke record created."))
        else:
            st.warning(smoke_result.get("message", "Google Drive runtime is not connected."))
        st.write(f"Result: {'Success' if smoke_result.get('success') else 'Failed'}")
        st.write("Target: MANDITRADE_DB/14_runtime/drive_smoke_test.json")
        st.write(f"Mode: {'Service Account' if smoke_result.get('mode') == 'GOOGLE_DRIVE' else 'Local Mirror'}")
        st.write(f"File ID: {smoke_result.get('file_id', '') or 'Not available'}")
        st.write(f"Path / Location: {smoke_result.get('path', '')}")
        st.write(f"Timestamp: {smoke_result.get('last_updated', '')}")
        st.write(f"Message: {smoke_result.get('message', '')}")

    with st.expander("Advanced Details", expanded=False):
        st.markdown("### Validation Report")
        st.json(validation, expanded=False)
        st.markdown("### Bootstrap Report")
        st.json(latest_bootstrap or {}, expanded=False)
        st.markdown("### Structure Report")
        st.json(latest_structure or {}, expanded=False)
