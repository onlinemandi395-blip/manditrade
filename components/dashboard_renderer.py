from __future__ import annotations

import streamlit as st

from components.card_renderer import render_metric_card


def render_dashboard_cards(cards: list[dict], dataset_lookup: dict[str, list[dict]], translator) -> None:
    columns = st.columns(max(len(cards), 1))
    for column, card in zip(columns, cards):
        dataset_name = str(card.get("data_source", ""))
        rows = dataset_lookup.get(dataset_name, [])
        metric = card.get("metric", "count")
        value = len(rows) if metric == "count" else 0
        with column:
            render_metric_card(translator.t(card.get("title_key", card.get("id", ""))), str(value), dataset_name)
