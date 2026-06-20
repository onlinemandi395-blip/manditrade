from __future__ import annotations

import json
from collections import Counter

import streamlit.components.v1 as components

from components.html_renderer import load_template


def _recent_activity_series(rows: list[dict], *, key: str = "created_at") -> list[int]:
    counts = Counter()
    for row in rows:
        stamp = str(row.get(key, "") or "").strip()
        if len(stamp) >= 10:
            counts[stamp[:10]] += 1
    ordered_days = sorted(counts.keys())[-7:]
    if not ordered_days:
        return [0, 0, 0, 0, 0, 0, 0]
    series = [counts[day] for day in ordered_days]
    while len(series) < 7:
        series.insert(0, 0)
    return series


def _status_series(rows: list[dict], statuses: list[str], *, key: str = "status") -> list[int]:
    counts = Counter(str(row.get(key, "")).strip().upper() for row in rows)
    return [counts.get(status.upper(), 0) for status in statuses]


def _build_card_series(metric: str, rows: list[dict], current_user: dict) -> list[int | float]:
    current_email = str(current_user.get("email", "")).strip().lower()
    if metric in {"marketplace_orders", "manditrade_orders", "orders_received", "marketplace_orders_received", "manditrade_orders_received"}:
        scoped_rows = rows
        if metric == "marketplace_orders":
            scoped_rows = [row for row in rows if str(row.get("source_channel", "")).strip().lower() == "marketplace"]
        elif metric == "manditrade_orders":
            scoped_rows = [row for row in rows if str(row.get("source_channel", "")).strip().lower() == "manditrade"]
        elif metric == "marketplace_orders_received":
            scoped_rows = [
                row for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("source_channel", "")).strip().lower() == "marketplace"
            ]
        elif metric == "manditrade_orders_received":
            scoped_rows = [
                row for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("source_channel", "")).strip().lower() == "manditrade"
            ]
        elif metric == "orders_received":
            scoped_rows = [row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email]
        return _recent_activity_series(scoped_rows)
    if metric in {"pending_orders", "completed_orders"}:
        scoped_rows = [row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email]
        return _status_series(scoped_rows, ["PAYMENT_PENDING", "OWNER_ACCEPTED", "PICKUP_ASSIGNED", "IN_TRANSIT", "COMPLETED"])
    if metric in {"active_shipments", "my_active_shipments"}:
        scoped_rows = rows if metric == "active_shipments" else [row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email]
        return _status_series(scoped_rows, ["PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED"])
    if metric in {"mahajans_count", "client_buyers_count", "public_buyers_count", "workers_count"}:
        role_map = {
            "mahajans_count": "mahajan",
            "client_buyers_count": "client_buyer",
            "public_buyers_count": "public_buyer",
            "workers_count": "worker",
        }
        if metric == "workers_count":
            scoped_rows = [row for row in rows if str(row.get("role", "")).strip().lower() in {"worker", "delivery_partner"}]
        else:
            scoped_rows = [row for row in rows if str(row.get("role", "")).strip().lower() == role_map[metric]]
        return _recent_activity_series(scoped_rows, key="created_at")
    if metric == "owned_products":
        scoped_rows = [row for row in rows if str(((row.get("owner") or {}).get("email", ""))).strip().lower() == current_email]
        return _recent_activity_series(scoped_rows)
    if metric == "low_stock_products":
        scoped_rows = [
            row for row in rows
            if float(((row.get("inventory") or {}).get("available_quantity", 0) or 0)) <= 10
        ]
        return [len(scoped_rows)]
    if metric in {"unread_notifications", "worker_notifications"}:
        return _recent_activity_series(rows)
    if metric in {"ledger_balance", "open_ledger", "platform_margin_total"}:
        grouped = Counter(str(row.get("entry_type", "")).strip().upper() for row in rows)
        return [
            grouped.get("PAYABLE_TO_OWNER", 0),
            grouped.get("PAYMENT_TO_OWNER", 0),
            grouped.get("PLATFORM_MARGIN", 0),
            grouped.get("PACKAGING_FEE", 0),
            grouped.get("SHIPPING_FEE", 0),
        ]
    if metric in {"payments_total", "pending_payments_total"}:
        scoped_rows = rows if metric == "payments_total" else [
            row for row in rows if str(row.get("payment_status", row.get("status", ""))).strip().upper() in {"PENDING", "PAYMENT_PENDING"}
        ]
        return _recent_activity_series(scoped_rows)
    return _recent_activity_series(rows)


def _resolve_card_value(card: dict, rows: list[dict], current_user: dict) -> int | float:
    metric = card.get("metric", "count")
    current_email = str(current_user.get("email", "")).strip().lower()
    current_role = str(current_user.get("role", "")).strip().lower()
    if metric == "mahajans_count":
        return len([row for row in rows if str(row.get("role", "")).strip().lower() == "mahajan"])
    if metric == "client_buyers_count":
        return len([row for row in rows if str(row.get("role", "")).strip().lower() == "client_buyer"])
    if metric == "public_buyers_count":
        return len([row for row in rows if str(row.get("role", "")).strip().lower() == "public_buyer"])
    if metric == "workers_count":
        return len([row for row in rows if str(row.get("role", "")).strip().lower() in {"worker", "delivery_partner"}])
    if metric == "owned_products":
        return len([row for row in rows if str(((row.get("owner") or {}).get("email", ""))).strip().lower() == current_email])
    if metric == "orders_received":
        return len([row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email])
    if metric == "marketplace_orders":
        return len([row for row in rows if str(row.get("source_channel", "")).strip().lower() == "marketplace"])
    if metric == "manditrade_orders":
        return len([row for row in rows if str(row.get("source_channel", "")).strip().lower() == "manditrade"])
    if metric == "marketplace_orders_received":
        return len(
            [
                row
                for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("source_channel", "")).strip().lower() == "marketplace"
            ]
        )
    if metric == "manditrade_orders_received":
        return len(
            [
                row
                for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("source_channel", "")).strip().lower() == "manditrade"
            ]
        )
    if metric == "pending_orders":
        return len(
            [
                row
                for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("status", "")).upper() in {
                    "PAYMENT_PENDING",
                    "PAYMENT_VERIFIED",
                    "OWNER_ACCEPTED",
                    "READY_FOR_PICKUP",
                    "PICKUP_ASSIGNED",
                    "PICKED_UP",
                    "IN_TRANSIT",
                }
            ]
        )
    if metric == "completed_orders":
        return len(
            [
                row
                for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("status", "")).upper() in {"COMPLETED", "DELIVERED", "CLOSED"}
            ]
        )
    if metric == "ledger_balance":
        return round(
            sum(
                float(row.get("credit", 0) or 0) - float(row.get("debit", 0) or 0)
                for row in rows
                if str(((row.get("party_owner") or row.get("party_b") or {}).get("email", ""))).strip().lower() == current_email
                or str(((row.get("party_admin") or row.get("party_a") or {}).get("email", ""))).strip().lower() == current_email
            ),
            2,
        )
    if metric == "open_ledger":
        return round(sum(float(row.get("credit", 0) or 0) - float(row.get("debit", 0) or 0) for row in rows if str(row.get("status", "")).upper() == "OPEN"), 2)
    if metric == "platform_margin_total":
        return round(sum(float(row.get("credit", row.get("amount", 0)) or 0) for row in rows if str(row.get("entry_type", "")).strip().upper() == "PLATFORM_MARGIN"), 2)
    if metric == "active_shipments":
        return len([row for row in rows if str(row.get("status", "")).strip().upper() in {"PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT"}])
    if metric == "my_active_shipments":
        return len([row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email and str(row.get("status", "")).strip().upper() in {"PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT"}])
    if metric == "payments_total":
        return round(sum(float(row.get("amount_payable", row.get("amount_due", 0)) or 0) for row in rows), 2)
    if metric == "pending_payments_total":
        return round(sum(float(row.get("amount_payable", row.get("amount_due", 0)) or 0) for row in rows if str(row.get("payment_status", row.get("status", ""))).strip().upper() in {"PENDING", "PAYMENT_PENDING"}), 2)
    if metric == "low_stock_products":
        return len([row for row in rows if float(((row.get("inventory") or {}).get("available_quantity", 0) or 0)) <= 10])
    if metric == "worker_notifications":
        return len([row for row in rows if str(row.get("status", "UNREAD")).upper() == "UNREAD"])
    if metric == "owner_pending_requests":
        return len([row for row in rows if str(row.get("status", "")).upper() == "PENDING_APPROVAL"])
    if metric == "unread_notifications":
        return len(
            [
                row
                for row in rows
                if str(row.get("status", "UNREAD")).upper() == "UNREAD"
                and (
                    current_role == "platform_admin"
                    or str(row.get("to_email", "")).strip().lower() == current_email
                    or current_email in {
                        str(recipient or "").strip().lower()
                        for recipient in (row.get("recipients", []) or [])
                        if str(recipient or "").strip()
                    }
                )
            ]
        )
    return len(rows) if metric == "count" else 0


def _format_metric_value(value: int | float) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:,.2f}"
    return f"{value:,}"


def render_dashboard_cards(cards: list[dict], dataset_lookup: dict[str, list[dict]], translator, current_user: dict | None = None) -> None:
    current_user = current_user or {}
    rendered_cards = []
    for card in cards:
        dataset_name = str(card.get("data_source", "")).strip()
        rows = dataset_lookup.get(dataset_name, [])
        rendered_cards.append(
            {
                "title": translator.t(card.get("title_key", card.get("id", ""))),
                "value": _format_metric_value(_resolve_card_value(card, rows, current_user)),
                "subtitle": translator.t(card.get("subtitle_key", "")) if str(card.get("subtitle_key", "")).strip() else (dataset_name.replace("_", " ").title() if dataset_name else "Workspace Metric"),
                "eyebrow": str(card.get("eyebrow", f"Metric {len(rendered_cards) + 1}")),
                "series": _build_card_series(str(card.get("metric", "count")), rows, current_user),
            }
        )

    if not rendered_cards:
        return

    payload_json = json.dumps(rendered_cards, ensure_ascii=True)
    markup = load_template("dashboard_cards.html", payload_json=payload_json)
    components.html(markup, height=min(max(360, 180 + (len(rendered_cards) * 40)), 980), scrolling=False)
