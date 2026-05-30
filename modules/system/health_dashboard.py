from __future__ import annotations

import streamlit as st


def render_health_dashboard(app_context: dict) -> None:
    st.subheader("System Health")
    lock_files = list((app_context["runtime_paths"]["base"] / "locks").glob("*.json"))
    transactions_dir = app_context["runtime_paths"]["base"] / "transactions"
    order_transactions_dir = app_context["runtime_paths"]["base"] / "order_transactions"
    recovered = []
    recovered_orders = []
    if st.button("Recover Incomplete Transactions", use_container_width=True):
        recovery_result = app_context["startup_recovery_service"].run_recovery_pass()
        recovered = recovery_result["procurement_recovered"]
        recovered_orders = recovery_result["order_recovered"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Drive Mode", app_context["drive_service"].describe_runtime_mode())
    col2.metric("OAuth Session", "Active" if app_context["current_user"] else "Idle")
    col3.metric("Gmail Trigger", "Runtime")
    col4.metric("Active Locks", len(lock_files))
    st.markdown("### Cloud Deployment Readiness")
    deployment_snapshot = {
        "runtime_environment": app_context["system_config"]["app"].get("runtime_environment", "local"),
        "redirect_uri": app_context["oauth_config"]["google_oauth"].get("redirect_uri", ""),
        "demo_mode": app_context["system_config"]["app"].get("demo_mode", False),
        "safe_mode": app_context["system_config"]["app"].get("safe_mode", False),
        "staging_mode": app_context["system_config"]["app"].get("staging_mode", False),
        "notification_mode": app_context.get("notification_mode", "mock"),
        "google_runtime_enabled": app_context.get("google_runtime_enabled", False),
        "long_lived_admin_runtime_enabled": app_context.get("long_lived_admin_runtime_enabled", False),
        "blockers": app_context.get("startup_checks", []),
        "warnings": app_context.get("startup_warnings", []),
        "pilot_status_report": str(app_context["runtime_paths"]["integration_reports"] / "latest_pilot_status.json"),
        "go_no_go": "NO-GO" if app_context.get("startup_checks") else "READY FOR CLOUD VALIDATION",
    }
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
    current_user = app_context["current_user"]
    if current_user and current_user.role == "admin":
        oauth_status = app_context["google_runtime_diagnostic_service"].oauth_status(current_user)
        with st.expander("OAuth Status", expanded=False):
            st.json(oauth_status)
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
    st.markdown("### Pilot Status")
    st.json(app_context.get("latest_pilot_status", {}))

    st.markdown("### Gmail Runtime Delivery")
    st.info("User-facing Gmail queues are disabled. Notification emails are triggered immediately from the active runtime session.")
    st.markdown("### Dead Letter Queue")
    st.dataframe(app_context["dead_letter_service"].list_entries(limit=50), use_container_width=True)
    st.markdown("### Runtime Metrics")
    st.json(runtime_metrics)
    st.markdown("### Recent Runtime Errors")
    st.dataframe(app_context["logging_service"].read_recent("drive_failures", limit=10), use_container_width=True)
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
