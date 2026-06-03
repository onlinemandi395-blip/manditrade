from __future__ import annotations

import streamlit as st

from components.background_tasks_panel import render_background_tasks_panel
from components.bulk_actions import render_bulk_actions
from components.data_grid import render_data_grid
from components.responsive_layout import render_section_intro
from components.toast_manager import push_toast
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes


def render_health_dashboard(app_context: dict) -> None:
    render_page_header(
        "System Health",
        "Inspect runtime readiness, recovery, diagnostics, dead letters, and deployment posture from one admin-only operational surface.",
        ["Admin Only", "Diagnostics", "Recovery"],
        role="Platform Admin",
        metrics=[("Drive Mode", app_context["drive_service"].describe_runtime_mode()), ("Storage Mode", app_context["system_config"]["storage"].get("mode", "compatibility")), ("Gmail", "Runtime trigger")],
        kicker="Digital Manpur Runtime Deck",
    )
    lock_files = list((app_context["runtime_paths"]["base"] / "locks").glob("*.json"))
    transactions_dir = app_context["runtime_paths"]["base"] / "transactions"
    order_transactions_dir = app_context["runtime_paths"]["base"] / "order_transactions"
    recovered = []
    recovered_orders = []
    if st.button("Recover Incomplete Transactions", use_container_width=True):
        recovery_result = app_context["startup_recovery_service"].run_recovery_pass()
        recovered = recovery_result["procurement_recovered"]
        recovered_orders = recovery_result["order_recovered"]

    render_metric_grid(
        [
            render_metric_card("Drive Mode", app_context["drive_service"].describe_runtime_mode(), "OPEN"),
            render_metric_card("OAuth Session", "Active" if app_context["current_user"] else "Idle", "SUCCESS" if app_context["current_user"] else "PENDING"),
            render_metric_card("Gmail Trigger", "Runtime", "OPEN"),
            render_metric_card("Active Locks", str(len(lock_files)), "WARNING" if lock_files else "SUCCESS"),
        ]
    )
    render_showcase_strip(
        [
            ("Deployment", app_context["system_config"]["app"].get("runtime_environment", "local"), "OPEN"),
            ("Safe Mode", str(app_context["system_config"]["app"].get("safe_mode", False)), "SUCCESS"),
            ("Startup Blockers", str(len(app_context.get("startup_checks", []))), "HIGH_PRIORITY" if app_context.get("startup_checks") else "SUCCESS"),
        ]
    )
    render_section_intro("Cloud Deployment Readiness", "Use this page for diagnostics and recovery. It stays dense and readable instead of trying to behave like a storefront.")
    deployment_snapshot = {
        "runtime_environment": app_context["system_config"]["app"].get("runtime_environment", "local"),
        "redirect_uri": app_context["oauth_config"]["google_oauth"].get("redirect_uri", ""),
        "demo_mode": app_context["system_config"]["app"].get("demo_mode", False),
        "safe_mode": app_context["system_config"]["app"].get("safe_mode", False),
        "staging_mode": app_context["system_config"]["app"].get("staging_mode", False),
        "oauth_secrets_override_active": app_context.get("oauth_secrets_override_active", False),
        "oauth_config_fallback_active": app_context.get("oauth_config_fallback_active", False),
        "notification_mode": app_context.get("notification_mode", "mock"),
        "google_runtime_enabled": app_context.get("google_runtime_enabled", False),
        "long_lived_admin_runtime_enabled": app_context.get("long_lived_admin_runtime_enabled", False),
        "blockers": app_context.get("startup_checks", []),
        "warnings": app_context.get("startup_warnings", []),
        "pilot_status_report": str(app_context["runtime_paths"]["integration_reports"] / "latest_pilot_status.json"),
        "go_no_go": "NO-GO" if app_context.get("startup_checks") else "READY FOR CLOUD VALIDATION",
    }
    connected_accounts_summary = app_context["connected_accounts_service"].summarize_connections(
        [item.get("manufacturer_code", "") for item in app_context["governance_service"].list_manufacturers() if item.get("manufacturer_code")]
    )
    reliability_rows = _build_reliability_rows(app_context, lock_files)
    overview_tab, diagnostics_tab, recovery_tab, migration_tab, events_tab = st.tabs(["Overview", "Diagnostics", "Recovery", "Migration", "Events"])
    with overview_tab:
        st.json(deployment_snapshot)
        st.markdown("### Google Runtime")
        st.write(
        {
            "staging_mode": app_context["system_config"]["app"].get("staging_mode", False),
            "effective_demo_mode": app_context.get("effective_demo_mode", True),
            "google_runtime_enabled": app_context.get("google_runtime_enabled", False),
            "notification_mode": app_context.get("notification_mode", "mock"),
        }
        )
        st.markdown("### Pilot Status")
        st.json(app_context.get("latest_pilot_status", {}))
        st.markdown("### Connected Accounts Summary")
        st.json(connected_accounts_summary)
        st.markdown("### Gmail Runtime Delivery")
        st.info("User-facing Gmail queues are disabled. Notification emails are triggered immediately from the active runtime session.")
        st.markdown("### Operational Reliability")
        render_data_grid(
            page_key="health_reliability",
            rows=reliability_rows,
            search_fields=["metric", "status", "detail"],
            status_field="status",
            search_placeholder="Search reliability metrics",
        )

    current_user = app_context["current_user"]
    session_user = app_context.get("session_user") or current_user
    with diagnostics_tab:
        if current_user and app_context["security_service"].is_admin_identity(session_user):
            oauth_status = app_context["google_runtime_diagnostic_service"].oauth_status(current_user)
            with st.expander("OAuth Status", expanded=False):
                st.json(oauth_status)
                st.markdown("### OAuth Navigation + RCA")
                st.write(
                    {
                        "login_navigation_mode": oauth_status.get("login_navigation_mode", ""),
                        "last_oauth_failure_reason": oauth_status.get("last_oauth_failure_reason", ""),
                        "same_tab_rca_status": oauth_status.get("same_tab_rca_status", {}),
                        "state_persistence_mode": oauth_status.get("state_persistence_mode", ""),
                    }
                )
                st.markdown("### OAuth Recovery Checklist")
                st.markdown(
                    "\n".join(
                        [
                            "1. Google Cloud Console -> APIs & Services -> Credentials",
                            "2. Verify OAuth Client ID is active",
                            "3. Add redirect URI:",
                            "   - http://localhost:8501",
                            "   - https://manpur-mandi-trade.streamlit.app",
                            "4. Update Streamlit/local secrets with latest client_id/client_secret",
                            "5. Reboot app",
                        ]
                    )
                )
            admin_token_status = app_context["google_runtime_diagnostic_service"].admin_token_status()
            with st.expander("Admin Token Status", expanded=False):
                st.json(admin_token_status)
            if not admin_token_status["token_file_exists"] or admin_token_status["placeholder_detected"]:
                st.warning("Long-lived admin runtime mode is disabled until configs/admin_token.enc is provisioned with a real encrypted refresh token.")
            elif admin_token_status["error"]:
                st.warning("Admin token file exists but verification failed. Re-provision the admin token before relying on long-lived runtime mode.")
            col_a, col_b = st.columns(2)
            if col_a.button("Test Drive Access", use_container_width=True, disabled=not app_context.get("google_runtime_enabled", False)):
                result = app_context["google_runtime_diagnostic_service"].test_drive_access(
                    current_user,
                    safe_mode=app_context["system_config"]["app"].get("safe_mode", True),
                )
                st.json(result)
            if col_b.button("Test Gmail Send", use_container_width=True, disabled=not app_context.get("google_runtime_enabled", False)):
                result = app_context["google_runtime_diagnostic_service"].test_gmail_send(current_user)
                st.json(result)
        else:
            st.info("Google runtime diagnostics are available to the signed-in admin only.")
        runtime_metrics = app_context["runtime_metrics_service"].latest()
        st.markdown("### Dead Letter Queue")
        dead_letter_rows = app_context["dead_letter_service"].list_entries(limit=50)
        st.dataframe(dead_letter_rows, use_container_width=True)
        selected_ids, triggered_action = render_bulk_actions(
            page_key="health_dead_letters_bulk",
            rows=dead_letter_rows,
            id_field="entry_id",
            action_options=[("export_csv", "Export Dead Letters CSV"), ("export_json", "Export Dead Letters JSON")],
            selection_label="Select dead-letter entries",
        )
        selected_rows = [row for row in dead_letter_rows if row.get("entry_id") in selected_ids]
        if triggered_action == "export_csv" and selected_rows:
            st.download_button(
                "Download Selected Dead Letters CSV",
                export_rows_to_csv_bytes(selected_rows),
                file_name="dead-letters-selected.csv",
                mime="text/csv",
                use_container_width=True,
                key="dead_letters_export_csv",
            )
        if triggered_action == "export_json" and selected_rows:
            st.download_button(
                "Download Selected Dead Letters JSON",
                export_rows_to_json_bytes(selected_rows),
                file_name="dead-letters-selected.json",
                mime="application/json",
                use_container_width=True,
                key="dead_letters_export_json",
            )
        st.markdown("### Runtime Metrics")
        st.json(runtime_metrics)
        st.markdown("### Recent Runtime Errors")
        st.dataframe(app_context["logging_service"].read_recent("drive_failures", limit=10), use_container_width=True)

    with recovery_tab:
        st.markdown("### Recovery History")
        recovery_rows = []
        recovery_dir = app_context["runtime_paths"].get("recovery")
        if recovery_dir and recovery_dir.exists():
            for path in sorted(recovery_dir.glob("*.json"), reverse=True)[:20]:
                try:
                    import json
                    recovery_rows.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        st.dataframe(recovery_rows, use_container_width=True)
        st.markdown("### Transaction Recovery")
        if recovered:
            st.success(f"Recovered {len(recovered)} incomplete transactions.")
        if recovered_orders:
            st.success(f"Recovered {len(recovered_orders)} incomplete order transactions.")
        search_value = st.text_input("Search by transaction, order, agreement, or manufacturer")
        transaction_rows = []
        if transactions_dir.exists():
            for path in sorted(transactions_dir.glob("TXN-*.json")):
                try:
                    import json
                    transaction_rows.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        if search_value:
            transaction_rows = [row for row in transaction_rows if search_value.lower() in str(row).lower()]
        st.dataframe(transaction_rows, use_container_width=True)
        st.markdown("### Order Transaction Timeline")
        order_transaction_rows = []
        if order_transactions_dir.exists():
            for path in sorted(order_transactions_dir.glob("TXN-*.json")):
                try:
                    import json
                    order_transaction_rows.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        if search_value:
            order_transaction_rows = [row for row in order_transaction_rows if search_value.lower() in str(row).lower()]
        st.dataframe(order_transaction_rows, use_container_width=True)
        st.markdown("### Recovery Utilities")
        col1, col2 = st.columns(2)
        if col1.button("Rebuild Search Index", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "rebuild_search_index",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Search index rebuild queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        if col2.button("Refresh KPI Snapshot", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "refresh_kpi_snapshot",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"KPI refresh queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        col3, col4 = st.columns(2)
        if col3.button("Regenerate Alerts", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "regenerate_alerts",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Alert regeneration queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        if col4.button("Repair Snapshots", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "run_hourly_automation",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Automation refresh queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        st.markdown("### Background Tasks")
        render_background_tasks_panel(app_context, page_key="health_background_tasks", limit=15)

    with migration_tab:
        st.markdown("### Storage Migration")
        storage_mode = app_context["system_config"]["storage"].get("mode", "compatibility")
        cutover_service = app_context["storage_cutover_service"]
        latest_report = cutover_service.load_latest_migration_report()
        latest_dry_run = cutover_service.load_latest_migration_report(mode="dry_run")
        latest_execute = cutover_service.load_latest_migration_report(mode="execute")
        latest_validation = cutover_service.load_latest_validation_report()
        readiness_report = cutover_service.evaluate_cutover_readiness(storage_mode_current=storage_mode)
        st.json(
            {
                "storage_mode": storage_mode,
                "allow_legacy_fallback": app_context["system_config"]["storage"].get("allow_legacy_fallback", True),
                "canonical_root": str(app_context["drive_path_service"].db_root),
                "canonical_readiness": readiness_report["recommendation"],
            }
        )
        if st.button("Dry Run Storage Migration", use_container_width=True):
            latest_report = app_context["storage_migration_service"].run(mode="dry_run")
            st.success("Dry-run migration report generated.")
        if st.button("Validate Canonical Storage", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "rerun_canonical_validation",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Canonical validation queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        if st.button("Generate Cutover Readiness Report", use_container_width=True):
            task = app_context["recovery_action_service"].execute(
                "generate_cutover_readiness_report",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Cutover readiness report queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        validation_result = latest_validation or cutover_service.load_latest_validation_report() or app_context["canonical_storage_validation_service"].validate()
        readiness_report = cutover_service.evaluate_cutover_readiness(storage_mode_current=storage_mode)
        st.markdown("### Cutover Status")
        st.json(
            {
                "current_storage_mode": storage_mode,
                "last_dry_run_status": latest_dry_run.get("recommendation", "MISSING"),
                "last_execute_status": latest_execute.get("recommendation", "MISSING"),
                "last_validation_status": validation_result.get("status", "MISSING"),
                "canonical_readiness": readiness_report["recommendation"],
                "blocking_issues": readiness_report["blocking_issues"],
                "recommended_next_action": readiness_report["recommended_next_action"],
            },
            expanded=False,
        )
        st.markdown("### Latest Migration Report")
        st.json(latest_report, expanded=False)
        st.markdown("### Last Execute Report")
        st.json(latest_execute, expanded=False)
        st.markdown("### Canonical Validation")
        st.json(validation_result, expanded=False)
        st.markdown("### Cutover Readiness")
        st.json(readiness_report, expanded=False)
        st.info("Legacy files remain untouched. Switch `storage.mode` to `canonical` only after dry-run and validation review.")

    with events_tab:
        search_value = st.text_input("Search locks / events / stress summaries", key="health_events_search")
        st.markdown("### Stale Lock Viewer")
        lock_rows = []
        for path in lock_files:
            try:
                import json
                lock_rows.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        if search_value:
            lock_rows = [row for row in lock_rows if search_value.lower() in str(row).lower()]
        st.dataframe(lock_rows, use_container_width=True)

        st.markdown("### Emitted Domain Events")
        events_dir = app_context["runtime_paths"].get("events")
        event_rows = []
        if events_dir and events_dir.exists():
            for path in sorted(events_dir.glob("**/*.json"), reverse=True)[:50]:
                try:
                    import json
                    event_rows.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        if search_value:
            event_rows = [row for row in event_rows if search_value.lower() in str(row).lower()]
        st.dataframe(event_rows, use_container_width=True)
        st.markdown("### Stress Test Summaries")
        stress_dir = app_context["runtime_paths"]["base"] / "stress_reports"
        stress_rows = []
        if stress_dir.exists():
            for path in sorted(stress_dir.glob("*.json"), reverse=True)[:20]:
                try:
                    import json
                    stress_rows.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        st.dataframe(stress_rows, use_container_width=True)


def _build_reliability_rows(app_context: dict, lock_files: list) -> list[dict]:
    queue_count = len(app_context["gmail_service"].read_queue())
    dead_letters = app_context["dead_letter_service"].list_entries(limit=100)
    failed_notifications = len([item for item in dead_letters if "gmail" in str(item).lower() or "notification" in str(item).lower()])
    failed_tasks = len([item for item in dead_letters if "task" in str(item).lower() or "export" in str(item).lower()])
    storage_warnings = len(app_context.get("startup_warnings", []))
    return [
        {"metric": "Failed Task Count", "value": failed_tasks, "status": "WARNING" if failed_tasks else "SUCCESS", "detail": "Dead-letter task/export failures"},
        {"metric": "Retry Queue Count", "value": queue_count, "status": "WARNING" if queue_count else "SUCCESS", "detail": "Queued Gmail notifications pending processing"},
        {"metric": "Notification Failures", "value": failed_notifications, "status": "WARNING" if failed_notifications else "SUCCESS", "detail": "Dead-letter notification and Gmail failures"},
        {"metric": "Stale Locks", "value": len(lock_files), "status": "WARNING" if lock_files else "SUCCESS", "detail": "Runtime lock files present"},
        {"metric": "Storage Warnings", "value": storage_warnings, "status": "WARNING" if storage_warnings else "SUCCESS", "detail": "Startup and storage warning count"},
    ]
