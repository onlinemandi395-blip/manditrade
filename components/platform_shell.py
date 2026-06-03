from __future__ import annotations

from html import escape
from typing import Iterable

from components.html_renderer import render_html
from components.page_hero import render_page_hero


def render_platform_shell(
    *,
    title: str,
    subtitle: str,
    badges: list[str] | None = None,
    role: str | None = None,
    metrics: list[tuple[str, str]] | None = None,
    kicker: str = "MandiTrade Operating System",
    breadcrumbs: Iterable[str] | None = None,
    primary_actions: list[str] | None = None,
    secondary_actions: list[str] | None = None,
) -> None:
    crumb_html = ""
    if breadcrumbs:
        crumbs = list(breadcrumbs)
        crumb_html = "".join(
            f"<span class='mt-platform-shell__crumb'>{escape(item)}{'<span>/</span>' if index < len(crumbs) - 1 else ''}</span>"
            for index, item in enumerate(crumbs)
        )
    action_items = list(primary_actions or []) + list(secondary_actions or [])
    action_html = "".join(f"<span class='mt-action-chip'>{escape(item)}</span>" for item in action_items)
    render_html(
        f"""
        <section class="mt-platform-shell">
          <div class="mt-platform-shell__topbar">
            <div class="mt-platform-shell__crumbs">{crumb_html}</div>
            <div class="mt-platform-shell__actions">{action_html}</div>
          </div>
        </section>
        """
    )
    render_page_hero(
        title=title,
        subtitle=subtitle,
        badges=badges,
        role=role,
        metrics=metrics,
        kicker=kicker,
    )
