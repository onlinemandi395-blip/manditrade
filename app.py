from __future__ import annotations

import streamlit as st

from components.page_renderer import render_app


st.set_page_config(
    page_title="MandiTrade Next",
    page_icon="MT",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
