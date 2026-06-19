from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


def render_checkout_steps(*, title: str, item_count: int, total_amount: float) -> None:
    render_template("checkout_steps_open.html")
    step_cols = st.columns(3, gap="small")
    step_cols[0].markdown("**Step 1**  \nDelivery Details")
    step_cols[1].markdown(f"**Step 2**  \nOrder Summary ({item_count} items)")
    step_cols[2].markdown("**Step 3**  \nUPI Payment")
    st.caption(title)
    st.caption(f"Total payable: Rs. {float(total_amount or 0):g}")
    render_template("html_close_div.html")
