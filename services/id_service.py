from __future__ import annotations

import streamlit as st


class IdService:
    def __init__(self) -> None:
        st.session_state.setdefault("mt_next_ids", {})

    def next(self, prefix: str) -> str:
        counters = st.session_state["mt_next_ids"]
        counters[prefix] = int(counters.get(prefix, 0)) + 1
        return f"{prefix.upper()}_{counters[prefix]:04d}"
