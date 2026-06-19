from __future__ import annotations

from components.html_renderer import render_template
from components.status_chip import render_status_chip


def render_metric_card(title: str, value: str, subtitle: str = "") -> None:
    render_template("card_metric.html", title=title, value=value, subtitle=subtitle)


def render_entity_card(title: str, body: str, status: str = "") -> None:
    status_html = render_status_chip(status) if status else ""
    render_template("card_entity.html", title=title, body=body, status_html=status_html)
