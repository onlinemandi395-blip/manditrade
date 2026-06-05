from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.toast_manager import push_toast
from components.ui_shell import render_metric_card, render_page_header


def _create_smoke_record(app_context: dict) -> dict:
    admin_drive_database_service = app_context["admin_drive_database_service"]
    drive_path_service = app_context["drive_path_service"]
    safe_drive_write_service = app_context["safe_drive_write_service"]
    target = drive_path_service.get_runtime_path("") / "drive_smoke_test.json"
    payload = {
        "schema_version": 1,
        "status": "OK",
        "created_at": datetime.now(UTC).isoformat(),
        "runtime_backend": admin_drive_database_service.runtime_status(),
    }
    safe_drive_write_service.replace_document(target, payload)
    return {"path": str(target), "payload": payload}


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
    runtime = validation.get("runtime", root)
    canonical_readiness = "READY" if validation.get("status") == "PASS" and not validation.get("critical_errors") else "NOT READY"
    render_metric_grid(
        [
            render_metric_card("Drive Config", "CONNECTED" if root.get("root_folder_name") else "MISSING", "SUCCESS" if root.get("root_folder_name") else "WARNING"),
            render_metric_card("Validation", validation.get("status", "UNKNOWN"), "SUCCESS" if validation.get("status") == "PASS" else "WARNING"),
            render_metric_card("Bootstrap", latest_bootstrap.get("recommendation", "UNKNOWN"), "SUCCESS" if latest_bootstrap.get("recommendation") == "PASS" else "PENDING"),
            render_metric_card("Canonical Readiness", canonical_readiness, "SUCCESS" if canonical_readiness == "READY" else "WARNING"),
        ]
    )
    render_section_intro("Admin Drive Runtime", "This page reports the active root, validation state, local mirror fallback, and safe bootstrap status. It does not auto-switch storage mode.")
    st.json(
        {
            "drive_mode": app_context["drive_service"].describe_runtime_mode(),
            "storage_mode": app_context["system_config"]["storage"].get("mode", "compatibility"),
            "root_folder_name": root.get("root_folder_name", ""),
            "root_folder_id": root.get("root_folder_id", ""),
            "connection_status": "REACHABLE" if validation.get("root", {}).get("exists", False) else "UNREACHABLE",
            "runtime_backend": runtime.get("runtime_backend", ""),
            "drive_api_requested": runtime.get("drive_api_requested", False),
            "drive_api_ready": runtime.get("drive_api_ready", False),
            "runtime_reason": runtime.get("reason", root.get("runtime_reason", "")),
            "local_mirror_fallback": runtime.get("runtime_backend") == "local_path_mirror",
            "bootstrap_status": latest_bootstrap.get("recommendation", "MISSING"),
            "validation_status": validation.get("status", "UNKNOWN"),
            "files_count": len(service.drive_path_service.bootstrap_file_definitions()),
            "canonical_readiness": canonical_readiness,
        },
        expanded=False,
    )
    col1, col2, col3 = st.columns(3)
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
    col4, col5 = st.columns(2)
    if col4.button("Create Smoke Record", use_container_width=True):
        smoke = _create_smoke_record(app_context)
        push_toast(f"Smoke record written to {Path(smoke['path']).name}.", tone="success", title="Admin Drive DB")
        st.rerun()
    if col5.button("Refresh", use_container_width=True):
        st.rerun()
    if st.button("Generate Structure Report", use_container_width=True):
        service.generate_structure_report()
        push_toast("Structure report generated.", tone="info", title="Admin Drive DB")
        st.rerun()
    st.markdown("### Validation Report")
    st.json(validation, expanded=False)
    st.markdown("### Bootstrap Report")
    st.json(latest_bootstrap or {}, expanded=False)
    st.markdown("### Structure Report")
    st.json(latest_structure or {}, expanded=False)
    if not runtime.get("drive_api_ready", False):
        st.warning(runtime.get("reason") or "Admin Drive DB is using local mirror fallback because runtime Drive API access is not ready.")

