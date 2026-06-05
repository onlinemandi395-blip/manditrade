from __future__ import annotations

import streamlit as st


def render_form(form_definition: dict, translator, on_submit) -> None:
    field_values: dict[str, object] = {}
    with st.form(f"form_{form_definition.get('collection', 'unknown')}"):
        st.subheader(translator.t(form_definition.get("title_key", "")))
        for field in form_definition.get("fields", []):
            label = translator.t(field.get("label_key", field.get("name", "")))
            name = field.get("name", "")
            field_type = field.get("type", "text")
            if field_type == "number":
                field_values[name] = st.number_input(label, value=0.0)
            elif field_type == "checkbox":
                field_values[name] = st.checkbox(label, value=False)
            else:
                field_values[name] = st.text_input(label)
        if st.form_submit_button(translator.t(form_definition.get("submit_label_key", "action.save"))):
            on_submit(field_values)
