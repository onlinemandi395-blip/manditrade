from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html


def render_order_card(
    *,
    order_id: str,
    supplier: str,
    quantity: str,
    price: str,
    status: str,
    title: str = "",
    subtitle: str = "",
    packaging: str = "",
    courier: str = "",
    next_action: str = "",
    action_label: str = "View Detail",
    action_key: str,
    supporting_text: str = "",
) -> bool:
    meta_chips = []
    if packaging:
        meta_chips.append(f"<span class='mt-chip mt-logistics-mini'>Packaging: {escape(packaging)}</span>")
    if courier:
        meta_chips.append(f"<span class='mt-chip mt-logistics-mini'>Courier: {escape(courier)}</span>")
    if next_action:
        meta_chips.append(f"<span class='mt-chip mt-order-stage-chip'>Next: {escape(next_action)}</span>")
    supporting_html = f"<p>{escape(supporting_text)}</p>" if supporting_text else ""
    subtitle_html = f"<p class='mt-order-card__subtitle'>{escape(subtitle)}</p>" if subtitle else ""
    render_html(
        f"""
        <article class="mt-order-card mt-card mt-mandiplace-card">
          <div class="mt-order-card__meta">
            <span class="mt-chip">Order: {escape(order_id)}</span>
            <span class="mt-status-chip">{escape(status)}</span>
          </div>
          <h3>{escape(title or supplier)}</h3>
          {subtitle_html}
          {supporting_html}
          <div class="mt-chip-row">
            <span class="mt-chip">{escape(supplier)}</span>
            <span class="mt-chip">Qty: {escape(quantity)}</span>
            <span class="mt-price-chip">Price: {escape(price)}</span>
          </div>
          <div class="mt-chip-row">{''.join(meta_chips)}</div>
        </article>
        """
    )
    return st.button(action_label, key=action_key, use_container_width=True)
