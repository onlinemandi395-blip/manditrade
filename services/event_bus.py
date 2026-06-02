from __future__ import annotations

from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self.handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        for handler in self.handlers.get(event_type, []):
            handler(payload)
