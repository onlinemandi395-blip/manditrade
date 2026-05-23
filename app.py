from __future__ import annotations

import streamlit as st

from bootstrap.app_bootstrap import main


st.set_page_config(
    page_title="MandiTrade",
    page_icon="MT",
    layout="wide",
    initial_sidebar_state="expanded",
)


if __name__ == "__main__":
    main()
