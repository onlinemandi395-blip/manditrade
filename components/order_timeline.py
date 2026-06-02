from __future__ import annotations

from components.timeline import render_timeline

DEFAULT_TIMELINE_STEPS = [
    "PLACED",
    "VALIDATED",
    "CONFIRMED",
    "PROCUREMENT_REQUIRED",
    "AGREEMENT_PENDING",
    "ADVANCE_PENDING",
    "DISPATCH_READY",
    "DISPATCHED",
    "DELIVERED",
    "CLOSED",
]


def render_order_timeline_component(status: str, *, steps: list[str] | None = None, labels: dict[str, str] | None = None) -> None:
    render_timeline(status, steps=steps or DEFAULT_TIMELINE_STEPS, labels=labels)
