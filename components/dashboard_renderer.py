from __future__ import annotations

from collections import Counter
from html import escape
from urllib.parse import urlencode

import pandas as pd
import streamlit as st
try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  # pragma: no cover - runtime fallback for lean deploys
    plt = None
from components.html_renderer import render_html, render_template

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


def _resolve_card_route(card: dict) -> str:
    return str(card.get("route", "") or "").strip()


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
    return


def _build_sparkline_svg(series: list[int | float], *, height: int = 38) -> str:
    values = [float(value or 0) for value in (series or [0, 0, 0, 0, 0, 0, 0])]
    if not values:
        values = [0, 0, 0, 0, 0, 0, 0]
    width = 240
    max_value = max(max(values), 1.0)
    step = width / max(len(values) - 1, 1)
    points: list[tuple[float, float]] = []
    for index, value in enumerate(values):
        x = index * step
        y = height - ((value / max_value) * (height - 6)) - 3
        points.append((x, y))
    line_path = " ".join(f"{'M' if index == 0 else 'L'}{x:.2f},{y:.2f}" for index, (x, y) in enumerate(points))
    fill_path = f"{line_path} L {width},{height} L 0,{height} Z"
    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.8" fill="{WHITE}" stroke="{RED}" stroke-width="1.4"></circle>'
        for x, y in points
    )
    guides = "".join(
        f'<line x1="0" y1="{guide}" x2="{width}" y2="{guide}" stroke="rgba(255,255,255,0.08)" stroke-width="1"></line>'
        for guide in (8, 20, 32)
    )
    return (
        f'<svg class="mt-dashboard-preview__spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
        f"{guides}"
        f'<path d="{fill_path}" fill="rgba(217, 4, 41, 0.18)"></path>'
        f'<path d="{line_path}" fill="none" stroke="{RED}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"></path>'
        f"{dots}</svg>"
    )


def _current_query_params() -> dict[str, str]:
    params: dict[str, str] = {}
    for key in st.query_params.keys():
        value = st.query_params.get(key, "")
        normalized = str(value or "").strip()
        if normalized:
            params[str(key)] = normalized
    return params


def _build_query_href(**updates: str | None) -> str:
    params = _current_query_params()
    for key, value in updates.items():
        normalized_key = str(key)
        normalized_value = str(value or "").strip()
        if normalized_value:
            params[normalized_key] = normalized_value
        elif normalized_key in params:
            del params[normalized_key]
    query = urlencode(params)
    return f"?{query}" if query else "?"


def _consume_query_value(name: str) -> str:
    value = str(st.query_params.get(name, "") or "").strip()
    if value and name in st.query_params:
        del st.query_params[name]
    return value


def _peek_query_value(name: str) -> str:
    return str(st.query_params.get(name, "") or "").strip()


def _widget_preview_series(role: str, scoped: dict[str, list[dict]], index: int) -> list[int | float]:
    orders = scoped.get("orders", [])
    shipments = scoped.get("shipments", [])
    payments = scoped.get("payments", [])
    products = scoped.get("products", [])
    users = scoped.get("users", [])
    ledger = scoped.get("ledger", [])
    if role == "platform_admin":
        series_map = {
            0: _status_series(orders, ["PAYMENT_PENDING", "OWNER_ACCEPTED", "PICKUP_ASSIGNED", "IN_TRANSIT", "COMPLETED"]),
            1: _recent_activity_series(orders),
            2: _status_series(orders, ["marketplace", "manditrade"], key="source_channel"),
            3: _status_series(shipments, ["PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED"]),
            4: _recent_activity_series(payments),
            5: _recent_activity_series(products),
            6: _recent_activity_series(orders),
            7: _recent_activity_series(users),
            8: _recent_activity_series(ledger),
        }
        return series_map.get(index, _recent_activity_series(orders))
    series_map = {
        0: _status_series(orders, ["PAYMENT_PENDING", "OWNER_ACCEPTED", "PICKUP_ASSIGNED", "IN_TRANSIT", "COMPLETED"]),
        1: _recent_activity_series(orders),
        2: _status_series(orders, ["marketplace", "manditrade"], key="source_channel"),
        3: _status_series(shipments, ["PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT", "DELIVERED"]),
        4: _recent_activity_series(payments),
        5: _recent_activity_series(products),
        6: _status_series(products, ["0", "5", "10"], key="stock_band"),
        7: _recent_activity_series(ledger),
        8: _recent_activity_series(orders),
    }
    return series_map.get(index, _recent_activity_series(orders))


def _summary_filtered_rows(metric: str, rows: list[dict], current_user: dict) -> list[dict]:
    current_email = str(current_user.get("email", "")).strip().lower()
    if metric == "merchants_count":
        return [row for row in rows if str(row.get("role", "")).strip().lower() == "merchant"]
    if metric == "client_buyers_count":
        return [row for row in rows if str(row.get("role", "")).strip().lower() == "client_buyer"]
    if metric == "public_buyers_count":
        return [row for row in rows if str(row.get("role", "")).strip().lower() == "public_buyer"]
    if metric == "workers_count":
        return [row for row in rows if str(row.get("role", "")).strip().lower() in {"worker", "delivery_partner"}]
    if metric == "owned_products":
        return [row for row in rows if str(((row.get("owner") or {}).get("email", ""))).strip().lower() == current_email]
    if metric == "orders_received":
        return [row for row in rows if str(row.get("owner_email", "")).strip().lower() == current_email]
    if metric == "marketplace_orders":
        return [row for row in rows if str(row.get("source_channel", "")).strip().lower() == "marketplace"]
    if metric == "manditrade_orders":
        return [row for row in rows if str(row.get("source_channel", "")).strip().lower() == "manditrade"]
    if metric == "marketplace_orders_received":
        return [
            row
            for row in rows
            if str(row.get("owner_email", "")).strip().lower() == current_email
            and str(row.get("source_channel", "")).strip().lower() == "marketplace"
        ]
    if metric == "manditrade_orders_received":
        return [
            row
            for row in rows
            if str(row.get("owner_email", "")).strip().lower() == current_email
            and str(row.get("source_channel", "")).strip().lower() == "manditrade"
        ]
    if metric == "low_stock_products":
        return [row for row in rows if float(((row.get("inventory") or {}).get("available_quantity", 0) or 0)) <= 10]
    return rows


def _summary_series(metric: str, rows: list[dict], current_user: dict) -> list[int | float]:
    return _build_card_series(metric, rows, current_user)


def _series_detail_chart(title: str, series: list[int | float]):
    fig, ax = _new_chart(figsize=(7.0, 3.2))
    if fig is None or ax is None:
        return None
    values = [float(value or 0) for value in (series or [0, 0, 0, 0, 0, 0, 0])]
    positions = list(range(len(values)))
    ax.plot(positions, values, color=RED, linewidth=2.6, marker="o", markerfacecolor=WHITE, markeredgecolor=RED)
    ax.fill_between(positions, values, color=RED, alpha=0.18)
    ax.set_title(title)
    ax.set_xlabel("Point")
    ax.set_ylabel("Value")
    return fig


def _compact_table_markup(rows: list[dict], *, empty_message: str = "No related rows found.") -> str:
    if not rows:
        return f'<div class="mt-dashboard-detail__empty">{escape(empty_message)}</div>'
    frame = pd.DataFrame([dict(row or {}) for row in rows]).fillna("")
    if frame.empty:
        return f'<div class="mt-dashboard-detail__empty">{escape(empty_message)}</div>'
    limited_columns = list(frame.columns[:5])
    limited_rows = frame[limited_columns].head(6)
    headers = "".join(f"<th>{escape(str(column).replace('_', ' ').title())}</th>" for column in limited_columns)
    body_rows = []
    for record in limited_rows.to_dict(orient="records"):
        cells = []
        for column in limited_columns:
            value = record.get(column, "")
            text = str(value)
            if len(text) > 48:
                text = f"{text[:45]}..."
            cells.append(f"<td>{escape(text)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<div class="mt-dashboard-detail__table-shell">'
        '<table class="mt-dashboard-detail__table">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def _get_widget_specs(role: str, scoped: dict[str, list[dict]]) -> list[dict]:
    if role == "platform_admin":
        return [
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
    return [
            ("My Order Stage Flow", "See where your current orders are sitting right now.", lambda: _order_status_chart(scoped.get("orders", []))),
            ("My Sales Trend", "Track your order value across the latest active days.", lambda: _order_value_trend_chart(scoped.get("orders", []))),
            ("My Channel Mix", "Compare your marketplace and manditrade business share.", lambda: _channel_mix_chart(scoped.get("orders", []))),
            ("My Shipment Pipeline", "Watch what is awaiting pickup, moving, or delivered.", lambda: _shipment_status_chart(scoped.get("shipments", []))),
            ("My Payment Collection", "Measure pending money against confirmed receipts.", lambda: _payments_chart(scoped.get("payments", []))),
            ("My Product Categories", "See which categories make up your current catalog.", lambda: _category_chart(scoped.get("products", []), scoped.get("orders", []))),
            ("Low Stock Watch", "Catch products that may need replenishment soon.", lambda: _low_stock_chart(scoped.get("products", []))),
            ("My Ledger Mix", "Review payable value, margin share, packaging, and shipping lines.", lambda: _ledger_mix_chart(scoped.get("ledger", []))),
            ("Order Health", "Track how many orders are active versus completed.", lambda: _order_status_chart(scoped.get("orders", []))),
        ]


def _render_summary_cards(cards: list[dict], dataset_lookup: dict[str, list[dict]], current_user: dict) -> list[dict]:
    cards_markup = []
    summary_specs: list[dict] = []
    summary_cards = cards[:6]
    for index, card in enumerate(summary_cards):
        focus_id = f"summary_{index}"
        dataset_name = str(card.get("data_source", "")).strip()
        rows = dataset_lookup.get(dataset_name, [])
        metric = str(card.get("metric", "count"))
        filtered_rows = _summary_filtered_rows(metric, rows, current_user)
        series = _summary_series(metric, filtered_rows, current_user)
        summary_specs.append(
            {
                "focus_id": focus_id,
                "title": str(card.get("title", "")),
                "subtitle": str(card.get("subtitle", "")).strip(),
                "caption": str(card.get("eyebrow", "Summary")),
                "value": _format_metric_value(_resolve_card_value(card, rows, current_user)),
                "rows": filtered_rows,
                "series": series,
            }
        )
        cards_markup.append(
            (
                '<a class="mt-dashboard-preview__tile mt-dashboard-preview__tile--summary" href="{href}">'
                '<div class="mt-dashboard-preview__head">'
                '<span class="mt-dashboard-preview__eyebrow">{eyebrow}</span>'
                '<span class="mt-dashboard-preview__index">{index_label}</span>'
                "</div>"
                '<div class="mt-dashboard-preview__title">{title}</div>'
                '<div class="mt-dashboard-preview__value">{value}</div>'
                '<div class="mt-dashboard-preview__subtitle">{subtitle}</div>'
                "{sparkline}"
                '<div class="mt-dashboard-preview__hint">Inspect live records</div>'
                "</a>"
            ).format(
                href=f"{_build_query_href(mt_focus=focus_id)}#mt-dashboard-detail",
                eyebrow=escape(str(card.get("eyebrow", "Summary"))),
                index_label=f"{index + 1:02d}",
                title=escape(str(card.get("title", ""))),
                value=escape(_format_metric_value(_resolve_card_value(card, rows, current_user))),
                subtitle=escape(str(card.get("subtitle", "")).strip()),
                sparkline=_build_sparkline_svg(series),
            )
        )
    render_template("dashboard_overview.html", section_title="Business Snapshot", section_subtitle="Use the graph views below to inspect the live data on this same page.", section_class="mt-dashboard-preview__summary-grid", tiles_markup="".join(cards_markup))
    return summary_specs


def _render_widget_board(role: str, scoped: dict[str, list[dict]]) -> list[dict]:
    if plt is None:
        return []
    widget_specs = _get_widget_specs(role, scoped)
    widgets_markup = []
    widget_details: list[dict] = []
    for index, spec in enumerate(widget_specs):
        title, subtitle, chart_fn = spec
        focus_id = f"widget_{index}"
        widget_details.append({"focus_id": focus_id, "title": title, "subtitle": subtitle, "chart_fn": chart_fn})
        widgets_markup.append(
            (
                '<a class="mt-dashboard-preview__tile mt-dashboard-preview__tile--widget" href="{href}">'
                '<div class="mt-dashboard-preview__head">'
                '<span class="mt-dashboard-preview__eyebrow">Widget</span>'
                '<span class="mt-dashboard-preview__index">{index_label}</span>'
                "</div>"
                '<div class="mt-dashboard-preview__title">{title}</div>'
                '<div class="mt-dashboard-preview__subtitle">{subtitle}</div>'
                "{sparkline}"
                '<div class="mt-dashboard-preview__hint">Open graph detail</div>'
                "</a>"
            ).format(
                href=f"{_build_query_href(mt_focus=focus_id)}#mt-dashboard-detail",
                index_label=f"{index + 1:02d}",
                title=escape(title),
                subtitle=escape(subtitle),
                sparkline=_build_sparkline_svg(_widget_preview_series(role, scoped, index)),
            )
        )
    render_template("dashboard_overview.html", section_title="Business Widgets", section_subtitle="Open any graph view to load its detailed chart and related records below.", section_class="mt-dashboard-preview__widget-grid", tiles_markup="".join(widgets_markup))
    return widget_details


def _detail_rows_for_widget(focus_id: str, role: str, scoped: dict[str, list[dict]]) -> list[dict]:
    mapping = {
        "widget_0": scoped.get("orders", []),
        "widget_1": scoped.get("orders", []),
        "widget_2": scoped.get("orders", []),
        "widget_3": scoped.get("shipments", []),
        "widget_4": scoped.get("payments", []),
        "widget_5": scoped.get("products", []),
        "widget_6": scoped.get("orders", []) if role == "platform_admin" else scoped.get("products", []),
        "widget_7": scoped.get("users", []) if role == "platform_admin" else scoped.get("ledger", []),
        "widget_8": scoped.get("ledger", []) if role == "platform_admin" else scoped.get("orders", []),
    }
    return [dict(row or {}) for row in mapping.get(focus_id, [])]


def _render_focus_detail(focus_id: str, summary_specs: list[dict], widget_specs: list[dict], *, role: str, scoped: dict[str, list[dict]]) -> None:
    render_html('<div id="mt-dashboard-detail"></div>')
    summary_lookup = {item["focus_id"]: item for item in summary_specs}
    widget_lookup = {item["focus_id"]: item for item in widget_specs}
    if not focus_id:
        render_html(
            (
                '<section class="mt-dashboard-detail">'
                '<div class="mt-dashboard-detail__eyebrow">Detail Panel</div>'
                '<div class="mt-dashboard-detail__title">Select a graph</div>'
                '<div class="mt-dashboard-detail__subtitle">Every preview graph opens its live chart and related records right here without leaving the dashboard.</div>'
                '<div class="mt-dashboard-detail__empty mt-dashboard-detail__empty--hero">Choose any summary trend or widget graph from the left board.</div>'
                "</section>"
            )
        )
        return
    if focus_id in summary_lookup:
        item = summary_lookup[focus_id]
        render_html(
            (
                '<section class="mt-dashboard-detail">'
                '<div class="mt-dashboard-detail__header">'
                '<div>'
                '<div class="mt-dashboard-detail__eyebrow">{eyebrow}</div>'
                '<div class="mt-dashboard-detail__title">{title}</div>'
                '<div class="mt-dashboard-detail__subtitle">{subtitle}</div>'
                '</div>'
                '<a class="mt-dashboard-preview__back" href="{clear_href}">Clear</a>'
                '</div>'
                '<div class="mt-dashboard-detail__metric">{value}</div>'
                '</section>'
            ).format(
                eyebrow=escape(item["caption"]),
                title=escape(item["title"]),
                subtitle=escape(item["subtitle"] or item["caption"]),
                clear_href=_build_query_href(mt_focus=""),
                value=escape(item["value"]),
            )
        )
        figure = _series_detail_chart(item["title"], item["series"])
        if figure is not None:
            st.pyplot(figure, use_container_width=True)
            plt.close(figure)
        render_html(_compact_table_markup(item["rows"]))
        return
    if focus_id in widget_lookup:
        item = widget_lookup[focus_id]
        render_html(
            (
                '<section class="mt-dashboard-detail">'
                '<div class="mt-dashboard-detail__header">'
                '<div>'
                '<div class="mt-dashboard-detail__eyebrow">Graph View</div>'
                '<div class="mt-dashboard-detail__title">{title}</div>'
                '<div class="mt-dashboard-detail__subtitle">{subtitle}</div>'
                '</div>'
                '<a class="mt-dashboard-preview__back" href="{clear_href}">Clear</a>'
                '</div>'
                '</section>'
            ).format(
                title=escape(item["title"]),
                subtitle=escape(item["subtitle"]),
                clear_href=_build_query_href(mt_focus=""),
            )
        )
        figure = item["chart_fn"]()
        if figure is not None:
            st.pyplot(figure, use_container_width=True)
            plt.close(figure)
        else:
            render_html('<div class="mt-dashboard-detail__empty">No data available for this graph.</div>')
        render_html(_compact_table_markup(_detail_rows_for_widget(focus_id, role, scoped)))


def render_dashboard_cards(cards: list[dict], dataset_lookup: dict[str, list[dict]], translator, current_user: dict | None = None) -> str | None:
    current_user = current_user or {}
    focus_id = _peek_query_value("mt_focus")
    translated_cards = []
    for index, card in enumerate(cards):
        dataset_name = str(card.get("data_source", "")).strip()
        translated_cards.append(
            {
                **card,
                "title": translator.t(card.get("title_key", card.get("id", f"card_{index}"))),
                "subtitle": translator.t(card.get("subtitle_key", "")) if str(card.get("subtitle_key", "")).strip() else (dataset_name.replace("_", " ").title() if dataset_name else "Workspace Metric"),
                "eyebrow": str(card.get("eyebrow", f"Metric {index + 1}")),
            }
        )

    if not translated_cards:
        return None

    role = str(current_user.get("role", "")).strip().lower()
    scoped = _scoped_datasets(dataset_lookup, current_user)
    board_col, detail_col = st.columns([2.25, 1.05], gap="small")
    with board_col:
        summary_specs = _render_summary_cards(translated_cards, dataset_lookup, current_user)
        widget_specs = _render_widget_board(role, scoped)
    with detail_col:
        _render_focus_detail(focus_id, summary_specs, widget_specs, role=role, scoped=scoped)
    return None
