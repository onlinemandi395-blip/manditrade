from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape

import streamlit as st

from components.html_renderer import render_html

TOASTS_KEY = "mt_toasts"
TOAST_TTL_SECONDS = 4


def push_toast(message: str, *, tone: str = "success", title: str = "") -> None:
    queue = list(st.session_state.get(TOASTS_KEY, []))
    queue.append(
        {
            "message": str(message or "").strip(),
            "tone": str(tone or "info").strip().lower(),
            "title": str(title or "").strip(),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    st.session_state[TOASTS_KEY] = queue[-5:]


def _live_toasts() -> list[dict]:
    live: list[dict] = []
    now = datetime.now(UTC)
    for item in list(st.session_state.get(TOASTS_KEY, [])):
        try:
            created = datetime.fromisoformat(str(item.get("created_at", "")))
        except ValueError:
            created = now
        if now - created <= timedelta(seconds=TOAST_TTL_SECONDS):
            live.append(item)
    st.session_state[TOASTS_KEY] = live
    return live


def render_toasts() -> None:
    toasts = _live_toasts()
    if not toasts:
        return
    cards = "".join(
        f"""
        <article class="mt-toast mt-toast--{escape(item.get('tone', 'info'))}">
          {f"<strong>{escape(item.get('title', ''))}</strong>" if item.get("title") else ""}
          <span>{escape(item.get('message', ''))}</span>
        </article>
        """
        for item in toasts
    )
    render_html(f"<section class='mt-toast-stack'>{cards}</section>")
