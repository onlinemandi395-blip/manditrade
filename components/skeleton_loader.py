from __future__ import annotations

from components.html_renderer import render_html


def render_skeleton_loader(*, kind: str = "card", count: int = 3) -> None:
    class_name = "mt-skeleton"
    blocks = "".join(f"<div class='{class_name}' style='height:{'72px' if kind == 'card' else '220px'}; margin-bottom:12px;'></div>" for _ in range(max(1, count)))
    render_html(f"<section>{blocks}</section>")
