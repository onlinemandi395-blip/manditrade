from __future__ import annotations

from components.order_detail_view import render_order_detail_view
from components.ui_shell import render_3d_panel


def render_detail_drawer(detail_payload: dict, *, title: str = "Detail Drawer", tone: str = "subtle") -> None:
    render_3d_panel("", title, tone=tone)
    render_order_detail_view(detail_payload)
