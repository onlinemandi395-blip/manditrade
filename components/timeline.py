from __future__ import annotations

from typing import Any

import streamlit as st

from utils.status_styles import get_status_style


def get_timeline_step_states(status: str, steps: list[str], history: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    current_index = steps.index(status) if status in steps else -1
    history_index = {str(item.get("status", "")): item for item in history or []}
    states: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        history_row = history_index.get(step, {})
        states.append(
            {
                "step": step,
                "is_complete": current_index >= index,
                "is_current": current_index == index,
                "timestamp": history_row.get("at", "") or history_row.get("timestamp", ""),
                "actor": history_row.get("actor", ""),
            }
        )
    return states


def render_timeline(status: str, *, steps: list[str], labels: dict[str, str] | None = None, history: list[dict[str, Any]] | None = None) -> None:
    step_states = get_timeline_step_states(status, steps, history)
    cols = st.columns(len(step_states)) if step_states else []
    for column, step_state in zip(cols, step_states):
        with column:
            style = get_status_style("ACTIVE" if step_state["is_complete"] else "INACTIVE")
            border = "3px solid #0f172a" if step_state["is_current"] else "1px solid #cbd5e1"
            label = (labels or {}).get(step_state["step"], step_state["step"].replace("_", " ").title())
            actor = str(step_state.get("actor", "") or "").strip()
            timestamp = str(step_state.get("timestamp", "") or "").strip()
            st.markdown(
                f"""
                <div style="text-align:center;padding:0.25rem 0.1rem;">
                  <div style="width:20px;height:20px;margin:0 auto 0.45rem;background:{style['color']};border-radius:999px;border:{border};"></div>
                  <div style="font-size:0.74rem;color:{style['color']};font-weight:700;">{label}</div>
                  <div style="font-size:0.66rem;color:#475569;">{actor or "&nbsp;"}</div>
                  <div style="font-size:0.62rem;color:#94a3b8;">{timestamp or "&nbsp;"}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
