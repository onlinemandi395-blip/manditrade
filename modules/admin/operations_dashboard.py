from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.filter_bar import render_filter_bar
from components.paginated_table import render_paginated_table
from components.responsive_layout import render_section_intro
from components.skeleton_loader import render_skeleton_loader
from utils.deep_links import activate_deep_link
from utils.page_ui import render_empty_state, render_metric_button_row


def render_operations_dashboard(app_context: dict) -> None:
    page_key = "operations_center"
    current_user = app_context["current_user"]
    render_platform_shell(
        title="Operations Center",
        subtitle="Single-pane command center for live commerce health, supply friction, finance risk, workforce activity, and platform governance.",
        badges=["Platform Admin", "Operational Intelligence"],
        role=current_user.role.replace("_", " ").title() if current_user else "Admin",
        breadcrumbs=["Platform", "Operations", "Operations Center"],
        primary_actions=["Run Hourly Tasks", "Run Daily Tasks"],
    )
    kpis = app_context["kpi_service"].read_latest_snapshot() or app_context["kpi_service"].calculate_snapshot(app_context)
    new_alerts = []
    alerts = app_context["alert_engine"].list_alerts(resolved=False)
    recommendations = (app_context["recommendation_service"].read_latest() or {}).get("recommendations", {}) or app_context["recommendation_service"].generate(app_context)
    audit_summary = app_context["audit_service"].summarize_structured_events()

    render_kpi_cards(
        [
            {"label": "Marketplace Orders Today", "value": str(kpis["marketplace"]["orders_today"]), "status": "OPEN"},
            {"label": "Active Mandi Orders", "value": str(kpis["mandi"]["active_orders"]), "status": "PENDING"},
            {"label": "MandiPlace Orders", "value": str(len(app_context["procurement_transaction_service"].list_mandiplace_orders())), "status": "OPEN"},
            {"label": "Pending Deliveries", "value": str(len([item for item in app_context["public_order_service"].list_all_orders() if str(item.get("status", "")).upper() == "DISPATCHED"]) + len([item for item in app_context["governance_service"].list_supply_orders() if str(item.get("status", "")).upper() == "MAHAJAN_DISPATCHED"])), "status": "HIGH"},
            {"label": "Open Alerts", "value": str(len(alerts)), "status": "CRITICAL" if len([item for item in alerts if str(item.get("severity", "")).upper() == "CRITICAL"]) else "WARNING"},
            {"label": "Platform Health", "value": str(kpis["health_scores"]["platform"]), "status": "SUCCESS" if kpis["health_scores"]["platform"] >= 70 else "WARNING"},
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Commerce Health", "value": str(kpis["marketplace"]["orders_today"]), "tab_name": "Commerce Health"},
            {"label": "Supply Health", "value": str(kpis["supply"]["low_stock_frequency"]), "tab_name": "Supply Health"},
            {"label": "Financial Health", "value": str(kpis["finance"]["commission_pending"]), "tab_name": "Financial Health"},
            {"label": "Workforce Health", "value": str(kpis["workforce"]["jobs_filled"]), "tab_name": "Workforce Health"},
            {"label": "Platform Health", "value": str(audit_summary["total_events"]), "tab_name": "Platform Health"},
        ],
    )
    commerce_tab, supply_tab, finance_tab, workforce_tab, platform_tab, alerts_tab, recs_tab, search_tab, automation_tab = st.tabs(
        ["Commerce Health", "Supply Health", "Financial Health", "Workforce Health", "Platform Health", "Alerts", "Recommendations", "Search", "Automation"]
    )

    with commerce_tab:
        render_section_intro("Commerce Health", "Marketplace, mandi, and supply workflow volume in one place.")
        st.dataframe(
            [
                {"metric": "Marketplace Orders Today", "value": kpis["marketplace"]["orders_today"]},
                {"metric": "Marketplace Revenue Today", "value": kpis["marketplace"]["revenue_today"]},
                {"metric": "Active Mandi Orders", "value": kpis["mandi"]["active_orders"]},
                {"metric": "MandiPlace Procurement Orders", "value": len(app_context["procurement_transaction_service"].list_mandiplace_orders())},
                {"metric": "Pending Deliveries", "value": len([item for item in app_context["public_order_service"].list_all_orders() if str(item.get("status", "")).upper() == "DISPATCHED"])},
            ],
            use_container_width=True,
        )
    with supply_tab:
        render_section_intro("Supply Health", "Low stock, delayed dispatches, and stalled mandi workflows surface here.")
        st.dataframe(
            [
                {"metric": "Low Stock Alerts", "value": kpis["supply"]["low_stock_frequency"]},
                {"metric": "Dispatch Rate %", "value": kpis["supply"]["dispatch_rate"]},
                {"metric": "Delayed Delivery %", "value": kpis["supply"]["delayed_delivery_percent"]},
                {"metric": "Supplier Response Hours", "value": kpis["mandi"]["supplier_response_hours"]},
            ],
            use_container_width=True,
        )
    with finance_tab:
        render_section_intro("Financial Health", "Outstanding ledgers and pending commissions stay visible without turning this into full accounting software.")
        st.dataframe(
            [
                {"metric": "Outstanding Ledger", "value": kpis["finance"]["outstanding_ledger"]},
                {"metric": "Overdue %", "value": kpis["finance"]["overdue_percent"]},
                {"metric": "Pending Commission", "value": kpis["finance"]["commission_pending"]},
                {"metric": "New Alerts", "value": len(new_alerts)},
            ],
            use_container_width=True,
        )
    with workforce_tab:
        render_section_intro("Workforce Health", "Jobs and worker participation remain part of the operations view.")
        st.dataframe(
            [
                {"metric": "Jobs Filled", "value": kpis["workforce"]["jobs_filled"]},
                {"metric": "Worker Response Rate %", "value": kpis["workforce"]["worker_response_rate"]},
                {"metric": "Inactive Workers", "value": kpis["workforce"]["inactive_workers"]},
                {"metric": "Pending Applications", "value": len(app_context["job_service"].list_applications())},
            ],
            use_container_width=True,
        )
    with platform_tab:
        render_section_intro("Platform Health", "Audit activity, stale records, and health scoring for the full operating system.")
        st.dataframe(
            [
                {"metric": "Audit Events", "value": audit_summary["total_events"]},
                {"metric": "High Warning Events", "value": audit_summary["warning_events"]},
                {"metric": "Tracked Actors", "value": audit_summary["actors"]},
                {"metric": "Platform Health Score", "value": kpis["health_scores"]["platform"]},
            ],
            use_container_width=True,
        )
    with alerts_tab:
        if not alerts:
            render_skeleton_loader(kind="table", count=1)
        filtered_alerts = render_data_grid(
            page_key="operations_alerts",
            rows=alerts,
            search_fields=["alert_id", "entity_id", "message", "type"],
            status_field="severity",
            date_field="created_at",
            search_placeholder="Search alerts by entity or message",
        )
        if filtered_alerts:
            selected_alert = st.selectbox("Resolve Alert", [item["alert_id"] for item in filtered_alerts], key="resolve_ops_alert")
            if st.button("Mark Alert Resolved", use_container_width=True):
                app_context["alert_engine"].resolve_alert(selected_alert)
                st.success("Alert resolved.")
                st.rerun()
        else:
            render_empty_state("No active alerts right now.")
    with recs_tab:
        admin_recommendations = recommendations.get("platform_admin", [])
        if admin_recommendations:
            st.dataframe(admin_recommendations, use_container_width=True)
        else:
            render_empty_state("No admin recommendations right now.")
    with search_tab:
        render_section_intro("Operational Search", "Search across orders, ledgers, manufacturers, mahajans, products, and raw materials.")
        query = st.text_input("Global Search", placeholder="Search order ID, manufacturer, mahajan, product, payment, or raw material")
        results = app_context["operational_search_service"].search(app_context, query)
        if results:
            st.dataframe([{k: v for k, v in item.items() if k != "target"} for item in results], use_container_width=True)
            selected_result = st.selectbox("Open Search Result", range(len(results)), format_func=lambda idx: f"{results[idx]['entity_type']} | {results[idx]['label']}")
            if st.button("Open Result", use_container_width=True):
                activate_deep_link(results[selected_result]["target"])
                st.rerun()
        elif query.strip():
            render_empty_state("No operational records matched that search.")
    with automation_tab:
        render_section_intro("Automation Tasks", "Run deterministic hourly or daily maintenance tasks without external schedulers.")
        col1, col2 = st.columns(2)
        if col1.button("Run Hourly Tasks", use_container_width=True):
            st.json(app_context["automation_tasks"].run_hourly_tasks(app_context), expanded=False)
        if col2.button("Run Daily Tasks", use_container_width=True):
            st.json(app_context["automation_tasks"].run_daily_tasks(app_context), expanded=False)
        st.caption("These tasks recompute KPIs, generate alerts, refresh recommendations, and archive old logs.")
