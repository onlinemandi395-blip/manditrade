from __future__ import annotations

from html import escape

from components.html_renderer import render_html
from components.ui_shell import render_page_header


def render_page_hero(
    *,
    title: str,
    subtitle: str,
    badges: list[str] | None = None,
    role: str | None = None,
    metrics: list[tuple[str, str]] | None = None,
    kicker: str = "MandiTrade Operating System",
    primary_actions: list[str] | None = None,
    secondary_actions: list[str] | None = None,
) -> None:
    render_page_header(
        title,
        subtitle,
        badges,
        role=role,
        metrics=metrics,
        kicker=kicker,
    )
    actions = list(primary_actions or []) + list(secondary_actions or [])
    if not actions:
        return
    action_html = "".join(f"<span class='mt-action-chip'>{escape(action)}</span>" for action in actions)
    render_html(f"<div class='mt-page-hero__actions'>{action_html}</div>")
