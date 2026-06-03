from __future__ import annotations

from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card


def render_kpi_cards(cards: list[dict]) -> None:
    rendered = [
        render_metric_card(
            str(item.get("label", "")),
            str(item.get("value", "")),
            str(item.get("status", "SUCCESS")),
        )
        for item in cards
    ]
    render_metric_grid(rendered)
