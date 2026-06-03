from __future__ import annotations

from components.ui_shell import render_status_badge
from components.html_renderer import render_html


def render_status_chip(status: str) -> str:
    return render_status_badge(status)


def render_labeled_status_chip(label: str, status: str) -> None:
    render_html(f"<div class='mt-badge-row'><span class='mt-card__label'>{label}</span>{render_status_badge(status)}</div>")
