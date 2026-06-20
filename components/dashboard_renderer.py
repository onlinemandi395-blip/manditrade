from __future__ import annotations

import json
from collections import Counter

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  # pragma: no cover - runtime fallback for lean deploys
    plt = None

from components.html_renderer import load_template


RED = "#d90429"
RED_SOFT = "#8f1123"
BLACK = "#050505"
BLACK_SOFT = "#141414"
WHITE = "#ffffff"
WHITE_SOFT = "#f3f3f3"
GRID = "#3a3a3a"


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
    if metric in {"merchants_count", "client_buyers_count", "public_buyers_count", "workers_count"}:
        role_map = {
            "merchants_count": "merchant",
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
    if metric == "merchants_count":
        return len([row for row in rows if str(row.get("role", "")).strip().lower() == "merchant"])
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


def _rows_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(row or {}) for row in rows])


def _series_or_default(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in frame:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index, dtype="float64")


def _scoped_datasets(dataset_lookup: dict[str, list[dict]], current_user: dict) -> dict[str, list[dict]]:
    role = str(current_user.get("role", "")).strip().lower()
    email = str(current_user.get("email", "")).strip().lower()
    scoped = {name: [dict(row or {}) for row in rows] for name, rows in dataset_lookup.items()}
    if role != "merchant":
        return scoped

    scoped["products"] = [
        row for row in scoped.get("products", [])
        if str(((row.get("owner") or {}).get("email", ""))).strip().lower() == email
    ]
    scoped["orders"] = [
        row for row in scoped.get("orders", [])
        if str(row.get("owner_email", "")).strip().lower() == email
    ]
    scoped["shipments"] = [
        row for row in scoped.get("shipments", [])
        if str(row.get("owner_email", "")).strip().lower() == email
    ]
    scoped["payments"] = [
        row for row in scoped.get("payments", [])
        if str(row.get("receiver_owner_email", "")).strip().lower() == email
    ]
    scoped["ledger"] = [
        row for row in scoped.get("ledger", [])
        if str(((row.get("party_owner") or {}).get("email", row.get("owner_email", "")))).strip().lower() == email
    ]
    scoped["notifications"] = [
        row
        for row in scoped.get("notifications", [])
        if (
            str(row.get("to_email", "")).strip().lower() == email
            or str(row.get("owner_email", "")).strip().lower() == email
            or email in {
                str(recipient or "").strip().lower()
                for recipient in (row.get("recipients", []) or [])
                if str(recipient or "").strip()
            }
        )
    ]
    return scoped


def _apply_chart_style(ax) -> None:
    ax.set_facecolor(BLACK_SOFT)
    ax.tick_params(colors=WHITE, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.title.set_color(WHITE)
    ax.xaxis.label.set_color(WHITE)
    ax.yaxis.label.set_color(WHITE)
    ax.grid(color=GRID, linestyle="--", linewidth=0.6, alpha=0.45, axis="y")


def _new_chart(figsize: tuple[float, float] = (6.2, 3.4)):
    if plt is None:
        return None, None
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(BLACK)
    _apply_chart_style(ax)
    return fig, ax


def _render_chart(title: str, subtitle: str, draw_fn) -> None:
    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.caption(subtitle)
        figure = draw_fn()
        if figure is None:
            st.caption("No data available yet for this view.")
            return
        st.pyplot(figure, use_container_width=True)
        plt.close(figure)


def _order_status_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "status" not in frame:
        return None
    counts = frame["status"].fillna("Unknown").astype(str).value_counts().head(7)
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.bar(counts.index.tolist(), counts.values.tolist(), color=[RED, WHITE, RED_SOFT, WHITE_SOFT, RED, WHITE, RED_SOFT][: len(counts)])
    ax.set_ylabel("Orders")
    ax.set_xlabel("Stage")
    ax.tick_params(axis="x", rotation=25)
    return fig


def _order_value_trend_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "created_at" not in frame:
        return None
    frame["created_day"] = pd.to_datetime(frame["created_at"], errors="coerce").dt.strftime("%d %b")
    frame["total_amount"] = pd.to_numeric(_series_or_default(frame, "total_amount"), errors="coerce").fillna(0.0)
    trend = frame.dropna(subset=["created_day"]).groupby("created_day")["total_amount"].sum().tail(10)
    if trend.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    positions = list(range(len(trend)))
    values = trend.values.tolist()
    ax.plot(positions, values, color=RED, linewidth=2.6, marker="o", markerfacecolor=WHITE, markeredgecolor=RED)
    ax.fill_between(positions, values, color=RED, alpha=0.18)
    ax.set_xticks(positions, trend.index.tolist())
    ax.set_ylabel("Rs.")
    ax.set_xlabel("Day")
    ax.tick_params(axis="x", rotation=25)
    return fig


def _channel_mix_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "source_channel" not in frame:
        return None
    counts = frame["source_channel"].fillna("unknown").astype(str).str.title().value_counts()
    if counts.empty:
        return None
    fig, ax = _new_chart(figsize=(5.8, 3.4))
    if fig is None or ax is None:
        return None
    wedges, texts, autotexts = ax.pie(
        counts.values.tolist(),
        labels=counts.index.tolist(),
        colors=[RED, WHITE, RED_SOFT, WHITE_SOFT][: len(counts)],
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"edgecolor": BLACK, "linewidth": 1.2},
        textprops={"color": WHITE, "fontsize": 9},
    )
    for item in autotexts:
        item.set_color(BLACK)
        item.set_fontsize(8)
    ax.set_aspect("equal")
    return fig


def _shipment_status_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "status" not in frame:
        return None
    counts = frame["status"].fillna("Unknown").astype(str).value_counts()
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.barh(counts.index.tolist(), counts.values.tolist(), color=[WHITE, RED, WHITE_SOFT, RED_SOFT][: len(counts)])
    ax.set_xlabel("Shipments")
    ax.set_ylabel("Stage")
    return fig


def _payments_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty:
        return None
    status_key = "payment_status" if "payment_status" in frame else "status"
    amount_key = "amount_payable" if "amount_payable" in frame else "amount_due"
    frame[amount_key] = pd.to_numeric(_series_or_default(frame, amount_key), errors="coerce").fillna(0.0)
    grouped = frame.groupby(frame[status_key].fillna("Unknown").astype(str))[amount_key].sum().sort_values(ascending=False)
    if grouped.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.bar(grouped.index.tolist(), grouped.values.tolist(), color=[RED, WHITE, RED_SOFT, WHITE_SOFT][: len(grouped)])
    ax.set_ylabel("Rs.")
    ax.set_xlabel("Payment State")
    ax.tick_params(axis="x", rotation=20)
    return fig


def _category_chart(products: list[dict], orders: list[dict]):
    product_frame = _rows_frame(products)
    order_frame = _rows_frame(orders)
    if product_frame.empty or "product_id" not in product_frame:
        return None
    categories = product_frame[["product_id", "category"]].copy()
    categories["category"] = categories["category"].fillna("General").astype(str)
    if not order_frame.empty and "product_id" in order_frame:
        order_frame["total_amount"] = pd.to_numeric(_series_or_default(order_frame, "total_amount"), errors="coerce").fillna(0.0)
        merged = order_frame.merge(categories, on="product_id", how="left")
        grouped = merged.groupby("category")["total_amount"].sum().sort_values(ascending=False).head(6)
    else:
        grouped = categories["category"].value_counts().head(6)
    if grouped.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.bar(grouped.index.tolist(), grouped.values.tolist(), color=[RED, WHITE, RED_SOFT, WHITE_SOFT, RED, WHITE][: len(grouped)])
    ax.set_ylabel("Value")
    ax.set_xlabel("Category")
    ax.tick_params(axis="x", rotation=18)
    return fig


def _merchant_ranking_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "owner_email" not in frame:
        return None
    frame["total_amount"] = pd.to_numeric(_series_or_default(frame, "total_amount"), errors="coerce").fillna(0.0)
    grouped = frame.groupby("owner_email")["total_amount"].sum().sort_values(ascending=False).head(6)
    if grouped.empty:
        return None
    labels = [value.split("@")[0].replace(".", " ").title() for value in grouped.index.tolist()]
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.barh(labels, grouped.values.tolist(), color=[RED, WHITE, RED_SOFT, WHITE_SOFT, RED, WHITE][: len(grouped)])
    ax.set_xlabel("Rs.")
    ax.set_ylabel("Merchant")
    return fig


def _role_mix_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "role" not in frame:
        return None
    grouped = frame["role"].fillna("unknown").astype(str).str.replace("_", " ").str.title().value_counts()
    if grouped.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.bar(grouped.index.tolist(), grouped.values.tolist(), color=[WHITE, RED, WHITE_SOFT, RED_SOFT, RED][: len(grouped)])
    ax.set_ylabel("Users")
    ax.set_xlabel("Role")
    ax.tick_params(axis="x", rotation=18)
    return fig


def _ledger_mix_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "entry_type" not in frame:
        return None
    frame["amount"] = pd.to_numeric(_series_or_default(frame, "amount"), errors="coerce").fillna(0.0)
    grouped = frame.groupby("entry_type")["amount"].sum().sort_values(ascending=False)
    if grouped.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.bar(grouped.index.tolist(), grouped.values.tolist(), color=[RED, WHITE, RED_SOFT, WHITE_SOFT, RED][: len(grouped)])
    ax.set_ylabel("Rs.")
    ax.set_xlabel("Ledger Type")
    ax.tick_params(axis="x", rotation=22)
    return fig


def _low_stock_chart(rows: list[dict]):
    frame = _rows_frame(rows)
    if frame.empty or "inventory" not in frame or "product_name" not in frame:
        return None
    frame["available_quantity"] = frame["inventory"].apply(
        lambda item: float(((item or {}).get("available_quantity", 0) or 0)) if isinstance(item, dict) else 0.0
    )
    low_stock = frame.sort_values("available_quantity").head(6)
    if low_stock.empty:
        return None
    fig, ax = _new_chart()
    if fig is None or ax is None:
        return None
    ax.barh(low_stock["product_name"].tolist(), low_stock["available_quantity"].tolist(), color=[WHITE, RED, WHITE_SOFT, RED_SOFT, RED, WHITE][: len(low_stock)])
    ax.set_xlabel("Units")
    ax.set_ylabel("Product")
    return fig


def _render_analytics(current_user: dict, dataset_lookup: dict[str, list[dict]]) -> None:
    role = str(current_user.get("role", "")).strip().lower()
    if role not in {"platform_admin", "merchant"}:
        return
    if plt is None:
        return

    scoped = _scoped_datasets(dataset_lookup, current_user)
    st.markdown("### Business Snapshot")
    if role == "platform_admin":
        st.caption("A live management view across merchants, buyers, payments, shipping, and platform earnings.")
        chart_specs = [
            ("Order Stage Flow", "See which stage is filling up and where follow-up is needed.", lambda: _order_status_chart(scoped.get("orders", []))),
            ("Sales Trend", "Track order value movement over the latest activity window.", lambda: _order_value_trend_chart(scoped.get("orders", []))),
            ("B2C vs B2B Mix", "Understand channel split across marketplace and manditrade.", lambda: _channel_mix_chart(scoped.get("orders", []))),
            ("Shipment Pipeline", "Monitor the delivery load across pickup, transit, and completion.", lambda: _shipment_status_chart(scoped.get("shipments", []))),
            ("Payment Collection", "Compare pending and verified payment value at a glance.", lambda: _payments_chart(scoped.get("payments", []))),
            ("Category Performance", "See which categories are carrying the most business value.", lambda: _category_chart(scoped.get("products", []), scoped.get("orders", []))),
            ("Top Merchants by Sales", "Spot the merchants driving the most transaction value.", lambda: _merchant_ranking_chart(scoped.get("orders", []))),
            ("User Mix", "Review platform coverage across merchant, client, public, and worker roles.", lambda: _role_mix_chart(scoped.get("users", []))),
            ("Ledger Revenue Mix", "Track owner payable, platform margin, packaging, and shipping entries.", lambda: _ledger_mix_chart(scoped.get("ledger", []))),
        ]
    else:
        st.caption("A merchant view focused on product movement, revenue flow, delivery progress, and stock pressure.")
        chart_specs = [
            ("My Order Stage Flow", "See where your current orders are sitting right now.", lambda: _order_status_chart(scoped.get("orders", []))),
            ("My Sales Trend", "Track your order value across the latest active days.", lambda: _order_value_trend_chart(scoped.get("orders", []))),
            ("My Channel Mix", "Compare your marketplace and manditrade business share.", lambda: _channel_mix_chart(scoped.get("orders", []))),
            ("My Shipment Pipeline", "Watch what is awaiting pickup, moving, or delivered.", lambda: _shipment_status_chart(scoped.get("shipments", []))),
            ("My Payment Collection", "Measure pending money against confirmed receipts.", lambda: _payments_chart(scoped.get("payments", []))),
            ("My Product Categories", "See which categories make up your current catalog.", lambda: _category_chart(scoped.get("products", []), scoped.get("orders", []))),
            ("Low Stock Watch", "Catch products that may need replenishment soon.", lambda: _low_stock_chart(scoped.get("products", []))),
            ("My Ledger Mix", "Review payable value, margin share, packaging, and shipping lines.", lambda: _ledger_mix_chart(scoped.get("ledger", []))),
        ]

    for start in range(0, len(chart_specs), 2):
        columns = st.columns(2, gap="large")
        for column, spec in zip(columns, chart_specs[start:start + 2]):
            title, subtitle, chart_fn = spec
            with column:
                _render_chart(title, subtitle, chart_fn)


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
    _render_analytics(current_user, dataset_lookup)
