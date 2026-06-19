from __future__ import annotations

import json

import streamlit.components.v1 as components

from components.html_renderer import load_template


def _resolve_card_value(card: dict, rows: list[dict], current_user: dict) -> int | float:
    metric = card.get("metric", "count")
    current_email = str(current_user.get("email", "")).strip().lower()
    current_role = str(current_user.get("role", "")).strip().lower()
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
                "subtitle": dataset_name.replace("_", " ").title() if dataset_name else "Workspace Metric",
            }
        )

    if not rendered_cards:
        return

    payload_json = json.dumps(rendered_cards, ensure_ascii=True)
    markup = load_template("dashboard_cards.html", payload_json=payload_json)
    components.html(markup, height=min(max(180, 120 + (len(rendered_cards) * 56)), 520), scrolling=False)
