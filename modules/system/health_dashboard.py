from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip


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
        st.dataframe(app_context["dead_letter_service"].list_entries(limit=50), use_container_width=True)
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
            st.json(app_context["operational_search_service"].rebuild_index(app_context), expanded=False)
        if col2.button("Refresh KPI Snapshot", use_container_width=True):
            st.json(app_context["kpi_service"].calculate_snapshot(app_context), expanded=False)
        col3, col4 = st.columns(2)
        if col3.button("Regenerate Alerts", use_container_width=True):
            st.json(app_context["alert_engine"].generate_alerts(app_context), expanded=False)
        if col4.button("Repair Snapshots", use_container_width=True):
            st.json(app_context["automation_tasks"].run_daily_tasks(app_context), expanded=False)

    with migration_tab:
        st.markdown("### Storage Migration")
        st.json(
            {
                "storage_mode": app_context["system_config"]["storage"].get("mode", "compatibility"),
                "allow_legacy_fallback": app_context["system_config"]["storage"].get("allow_legacy_fallback", True),
                "canonical_root": str(app_context["drive_path_service"].db_root),
            }
        )
        migration_reports_dir = app_context["runtime_paths"]["base"] / "migration_reports"
        latest_report = {}
        latest_validation = {}
        latest_report_path = migration_reports_dir / "latest_migration_report.json"
        if latest_report_path.exists():
            import json
            latest_report = json.loads(latest_report_path.read_text(encoding="utf-8"))
        if st.button("Dry Run Storage Migration", use_container_width=True):
            latest_report = app_context["storage_migration_service"].run(mode="dry_run")
            st.success("Dry-run migration report generated.")
        if st.button("Validate Canonical Storage", use_container_width=True):
            latest_validation = app_context["canonical_storage_validation_service"].validate()
            st.success("Canonical validation completed.")
        validation_result = latest_validation or app_context["canonical_storage_validation_service"].validate()
        st.markdown("### Latest Migration Report")
        st.json(latest_report, expanded=False)
        st.markdown("### Canonical Validation")
        st.json(validation_result, expanded=False)
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
