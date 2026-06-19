from __future__ import annotations

import itertools
import re
from datetime import date, datetime
from decimal import Decimal
import html
import json
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from components.empty_state import render_empty_state
from components.html_renderer import load_template, render_template


_TABLE_INSTANCE_COUNTER = itertools.count()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "table"


def _format_column_name(name: str) -> str:
    label = str(name).replace("_", " ").strip()
    return label.title() if label else "Value"


def _stringify_nested_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return f"{value:g}" if isinstance(value, float) else str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        parts = []
        for key, nested_value in value.items():
            rendered = _stringify_nested_value(nested_value)
            if rendered:
                parts.append(f"{_format_column_name(str(key))}: {rendered}")
        return " | ".join(parts)
    if isinstance(value, (list, tuple, set)):
        parts = [_stringify_nested_value(item) for item in value]
        return ", ".join(part for part in parts if part)
    text = str(value).strip()
    if not text:
        return ""
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
            return _stringify_nested_value(parsed)
        except Exception:
            return text
    return text


def _coerce_rows(rows: list[Any]) -> list[dict]:
    coerced: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            coerced.append(row)
        else:
            coerced.append({"value": row})
    return coerced


def _normalize_rows(rows: list[Any]) -> pd.DataFrame:
    dataframe = pd.DataFrame(_coerce_rows(rows))
    if dataframe.empty:
        return dataframe
    dataframe = dataframe.fillna("")
    dataframe = dataframe.map(_stringify_nested_value)
    dataframe.columns = [_format_column_name(column) for column in dataframe.columns]
    return dataframe


def _filter_dataframe(dataframe: pd.DataFrame, query: str) -> pd.DataFrame:
    if dataframe.empty or not query.strip():
        return dataframe
    needle = query.strip().lower()
    mask = dataframe.astype(str).apply(lambda column: column.str.lower().str.contains(needle, na=False))
    return dataframe[mask.any(axis=1)]


def _build_html_table(title: str, dataframe: pd.DataFrame, table_key: str) -> str:
    rows = dataframe.to_dict(orient="records")
    payload = {
        "title": title,
        "columns": list(dataframe.columns),
        "rows": rows,
        "table_key": table_key,
    }
    payload_json = json.dumps(payload, ensure_ascii=True)
    escaped_title = html.escape(title)
    return load_template(
        "data_table.html",
        payload_json=payload_json,
        table_key=table_key,
        escaped_title=escaped_title,
    )


def render_table(rows: list[dict], *, caption: str = "") -> None:
    title = caption or "Data table"
    table_key = f"{_slugify(title)}_{next(_TABLE_INSTANCE_COUNTER)}"
    dataframe = _normalize_rows(rows)
    columns = list(dataframe.columns)
    preview_columns = ", ".join(columns[:4]) if columns else "No columns"
    if len(columns) > 4:
        preview_columns = f"{preview_columns} +{len(columns) - 4} more"

    with st.container():
        render_template("table_shell_open.html")
        header_left, header_right = st.columns([3, 2])
        with header_left:
            render_template("table_shell_title.html", title=title)
            render_template("table_shell_subtitle.html", subtitle="Browse records in a searchable workspace.")
            render_template("table_shell_meta.html", label="Visible fields", value=preview_columns)
        with header_right:
            render_template("table_shell_stats.html", rows=str(len(dataframe)), columns=str(len(dataframe.columns)))

        if dataframe.empty:
            render_empty_state("No rows found.")
            render_template("table_shell_close.html")
            return

        query = st.text_input(
            "Search table",
            key=f"{table_key}_search",
            placeholder="Search any value...",
            label_visibility="collapsed",
        )
        filtered = _filter_dataframe(dataframe, query)
        helper_left, helper_right = st.columns([3, 2])
        with helper_left:
            if query.strip() and filtered.empty:
                st.caption(f"No matches found for '{query.strip()}'.")
            else:
                st.caption(f"Showing {len(filtered)} of {len(dataframe)} rows")
        with helper_right:
            render_template("table_shell_hint.html", hint="Search, scan, and inspect without touching raw JSON.")
        table_height = min(max(280, 220 + (min(len(filtered), 10) * 34)), 760)
        components.html(
            _build_html_table(title, filtered, table_key),
            height=table_height,
            scrolling=False,
        )
        render_template("table_shell_close.html")
