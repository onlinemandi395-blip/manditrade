from __future__ import annotations

from html import escape

from components.html_renderer import render_html
from components.ui_shell import render_glass_section, render_page_header


def render_3d_background() -> None:
    render_html("<div class='mt-shell' aria-hidden='true'></div>")


def render_page_hero(
    title: str,
    subtitle: str,
    role: str,
    metrics: list[tuple[str, str]] | None = None,
    badges: list[str] | None = None,
) -> None:
    render_page_header(title, subtitle, badges or [], role=role, metrics=metrics)


def open_glass_section(title: str | None = None, body: str = "", *, class_name: str = "") -> None:
    render_glass_section(title, body, class_name=class_name)


def render_chip_row(items: list[str]) -> str:
    chips = "".join(f"<span class='mt-chip'>{escape(item)}</span>" for item in items)
    return f"<div class='mt-chip-row'>{chips}</div>"
