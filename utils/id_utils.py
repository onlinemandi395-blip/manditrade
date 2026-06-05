from __future__ import annotations


def format_id(prefix: str, number: int) -> str:
    return f"{prefix.upper()}_{number:04d}"
