from __future__ import annotations

from components.html_renderer import render_template


def render_empty_state(message: str) -> None:
    render_template("empty_state.html", message=message)
