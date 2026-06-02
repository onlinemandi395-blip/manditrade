from __future__ import annotations

from typing import Any

import streamlit as st

from components.timeline import render_timeline


def build_order_detail_payload(
    order: dict[str, Any],
    *,
    order_id_key: str,
    status: str,
    items: list[dict[str, Any]],
    timeline_steps: list[str],
    timeline_labels: dict[str, str] | None = None,
    status_history: list[dict[str, Any]] | None = None,
    logistics: dict[str, Any] | None = None,
    payment: dict[str, Any] | None = None,
    trust_badges: list[str] | None = None,
    next_action: str = "",
    audit_snippets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "order_id": str(order.get(order_id_key, "")),
        "status": status,
        "items": items,
        "timeline_steps": timeline_steps,
        "timeline_labels": timeline_labels or {},
        "status_history": status_history or [],
        "logistics": logistics or {},
        "payment": payment or {},
        "notes": str(order.get("notes", "") or order.get("mahajan_notes", "") or order.get("seller_note", "")),
        "trust_badges": trust_badges or [],
        "next_action": next_action,
        "audit_snippets": audit_snippets or [],
    }


def render_order_detail_view(detail: dict[str, Any], *, image_service=None, show_audit: bool = False) -> None:
    st.subheader(f"Order Detail: {detail.get('order_id', '')}")
    badge_row = detail.get("trust_badges", [])
    if badge_row:
        st.caption(" | ".join(badge_row))
    status_col, action_col = st.columns(2)
    status_col.metric("Status", str(detail.get("status", "")))
    action_col.metric("Next Action", str(detail.get("next_action", "") or "Track Progress"))
    render_timeline(
        str(detail.get("status", "")),
        steps=list(detail.get("timeline_steps", [])),
        labels=dict(detail.get("timeline_labels", {})),
        history=list(detail.get("status_history", [])),
    )
    item_rows = []
    for item in detail.get("items", []):
        row = dict(item)
        if image_service:
            image = image_service.get_display_image(item, label=str(item.get("name", "Item")))
            row["thumbnail"] = image.get("src", "")
        item_rows.append(row)
    if item_rows:
        st.dataframe(item_rows, use_container_width=True)
    logistics_col, payment_col = st.columns(2)
    with logistics_col:
        st.caption("Logistics")
        st.json(detail.get("logistics", {}), expanded=False)
    with payment_col:
        st.caption("Payment")
        st.json(detail.get("payment", {}), expanded=False)
    notes = str(detail.get("notes", "")).strip()
    if notes:
        st.caption("Notes")
        st.write(notes)
    if show_audit and detail.get("audit_snippets"):
        st.caption("Audit Snippets")
        st.json(detail.get("audit_snippets", []), expanded=False)
