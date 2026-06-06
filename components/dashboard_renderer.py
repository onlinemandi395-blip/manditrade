from __future__ import annotations

import streamlit as st

from components.card_renderer import render_metric_card


def _resolve_card_value(card: dict, rows: list[dict], current_user: dict) -> int | float:
    metric = card.get("metric", "count")
    current_email = str(current_user.get("email", "")).strip().lower()
    if metric == "owned_products":
        return len([row for row in rows if str(((row.get("owner") or {}).get("email", ""))).strip().lower() == current_email])
    if metric == "orders_received":
        return len([row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email])
    if metric == "pending_orders":
        return len(
            [
                row
                for row in rows
                if str(row.get("owner_email", "")).strip().lower() == current_email
                and str(row.get("status", "")).upper() in {"PLACED", "REQUESTED", "PENDING", "IN_PROGRESS"}
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
                float(row.get("amount", 0) or 0)
                for row in rows
                if str(((row.get("party_b") or {}).get("email", ""))).strip().lower() == current_email
                or str(((row.get("party_a") or {}).get("email", ""))).strip().lower() == current_email
            ),
            2,
        )
    if metric == "unread_notifications":
        return len(
            [
                row
                for row in rows
                if str((row.get("metadata") or {}).get("to_email", "")).strip().lower() in {"", current_email}
            ]
        )
    return len(rows) if metric == "count" else 0


def render_dashboard_cards(cards: list[dict], dataset_lookup: dict[str, list[dict]], translator, current_user: dict | None = None) -> None:
    columns = st.columns(max(len(cards), 1))
    for column, card in zip(columns, cards):
        dataset_name = str(card.get("data_source", ""))
        rows = dataset_lookup.get(dataset_name, [])
        value = _resolve_card_value(card, rows, current_user or {})
        with column:
            render_metric_card(translator.t(card.get("title_key", card.get("id", ""))), str(value), dataset_name)
