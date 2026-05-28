from __future__ import annotations

from components.html_renderer import render_html


def render_metric_grid(cards: list[str]) -> None:
    render_html(f"<section class='mt-grid mt-grid--metrics'>{''.join(cards)}</section>")


def render_action_grid(cards: list[str]) -> None:
    render_html(f"<section class='mt-grid mt-grid--actions'>{''.join(cards)}</section>")
