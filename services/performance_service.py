from __future__ import annotations

import time
from contextlib import contextmanager

import streamlit as st


class PerformanceService:
    METRICS_KEY = "mt_next_perf_metrics"

    def __init__(self) -> None:
        self._ensure_metrics_store()

    def _ensure_metrics_store(self) -> dict:
        metrics = st.session_state.get(self.METRICS_KEY)
        if not isinstance(metrics, dict):
            st.session_state[self.METRICS_KEY] = {}
        return st.session_state[self.METRICS_KEY]

    @contextmanager
    def measure(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics = self._ensure_metrics_store()
            metrics[name] = {
                "elapsed_ms": elapsed_ms,
                "recorded_at": time.time(),
            }

    def get_metrics(self) -> dict:
        return dict(self._ensure_metrics_store())

    def clear(self) -> None:
        self._ensure_metrics_store().clear()
