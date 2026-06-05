from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.html_renderer import render_html


def render_actor_card(
    *,
    actor_id: str,
    title: str,
    subtitle: str,
    status: str,
    completion_score: int,
    trust_tier: str,
    location: str = "",
    supporting_text: str = "",
    badges: list[str] | None = None,
    action_label: str = "View Detail",
    action_key: str,
) -> bool:
    badge_html = "".join(f"<span class='mt-chip'>{escape(badge)}</span>" for badge in (badges or [])[:4])
    location_html = f"<span class='mt-chip'>{escape(location)}</span>" if location else ""
    supporting_html = f"<p>{escape(supporting_text)}</p>" if supporting_text else ""
    render_html(
        f"""
        <article class="mt-card mt-actor-card">
          <div class="mt-order-card__meta">
            <span class="mt-chip">{escape(actor_id)}</span>
            <span class="mt-status-chip">{escape(status)}</span>
          </div>
          <h3>{escape(title)}</h3>
          <p class="mt-order-card__subtitle">{escape(subtitle)}</p>
          {supporting_html}
          <div class="mt-chip-row">
            <span class="mt-price-chip">Profile: {escape(str(completion_score))}%</span>
            <span class="mt-chip">Trust: {escape(trust_tier)}</span>
            {location_html}
          </div>
          <div class="mt-chip-row">{badge_html}</div>
        </article>
        """
    )
    return st.button(action_label, key=action_key, use_container_width=True)
