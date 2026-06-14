from __future__ import annotations

import streamlit as st


def render_checkout_steps(*, title: str, item_count: int, total_amount: float) -> None:
    st.markdown("<div class='mt-commerce-steps'>", unsafe_allow_html=True)
    step_cols = st.columns(3, gap="small")
    step_cols[0].markdown("**Step 1**  \nDelivery Details")
    step_cols[1].markdown(f"**Step 2**  \nOrder Summary ({item_count} items)")
    step_cols[2].markdown("**Step 3**  \nUPI Payment")
    st.caption(title)
    st.caption(f"Total payable: Rs. {float(total_amount or 0):g}")
    st.markdown("</div>", unsafe_allow_html=True)
