from __future__ import annotations

import html
import json

import streamlit.components.v1 as components


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
    markup = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
          color: #1f1a14;
        }}
        .mt-dashboard-grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
          padding: 0.05rem 0.05rem 0.35rem;
        }}
        .mt-dashboard-card {{
          position: relative;
          overflow: hidden;
          min-height: 168px;
          padding: 1.05rem;
          border-radius: 22px;
          background:
            radial-gradient(circle at top right, rgba(221, 161, 94, 0.18), transparent 30%),
            linear-gradient(180deg, rgba(255, 252, 247, 0.96), rgba(250, 242, 231, 0.88));
          border: 1px solid rgba(108, 76, 39, 0.12);
          box-shadow: 0 18px 40px rgba(77, 55, 28, 0.12);
        }}
        .mt-dashboard-card__eyebrow {{
          display: inline-flex;
          padding: 0.32rem 0.62rem;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #bc6c25;
          background: rgba(188, 108, 37, 0.08);
          border: 1px solid rgba(188, 108, 37, 0.16);
        }}
        .mt-dashboard-card__title {{
          margin-top: 0.9rem;
          font-size: 15px;
          font-weight: 700;
          line-height: 1.35;
          color: #1f1a14;
        }}
        .mt-dashboard-card__value {{
          margin-top: 1.2rem;
          font-size: 34px;
          font-weight: 800;
          line-height: 1;
          color: #1f1a14;
        }}
        .mt-dashboard-card__subtitle {{
          margin-top: 0.7rem;
          color: #6f6355;
          font-size: 13px;
        }}
      </style>
    </head>
    <body>
      <div class="mt-dashboard-grid" id="mt-dashboard-grid"></div>
      <script>
        const cards = {payload_json};
        const root = document.getElementById("mt-dashboard-grid");
        const escapeHtml = (value) => String(value ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
        root.innerHTML = cards.map((card, index) => `
          <article class="mt-dashboard-card">
            <div class="mt-dashboard-card__eyebrow">Metric ${'{'}index + 1{'}'}</div>
            <div class="mt-dashboard-card__title">${'{'}escapeHtml(card.title){'}'}</div>
            <div class="mt-dashboard-card__value">${'{'}escapeHtml(card.value){'}'}</div>
            <div class="mt-dashboard-card__subtitle">${'{'}escapeHtml(card.subtitle){'}'}</div>
          </article>
        `).join("");
        const height = Math.min(Math.max(document.body.scrollHeight + 12, 180), 520);
        if (window.parent) {{
          window.parent.postMessage({{ type: "streamlit:setFrameHeight", height }}, "*");
        }}
      </script>
    </body>
    </html>
    """
    components.html(markup, height=min(max(180, 120 + (len(rendered_cards) * 56)), 520), scrolling=False)
