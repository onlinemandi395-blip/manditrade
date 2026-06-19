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
from components.html_renderer import render_html


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
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        :root {{
          --mt-bg: rgba(255, 255, 255, 0.68);
          --mt-panel: rgba(255, 251, 244, 0.9);
          --mt-border: rgba(108, 76, 39, 0.14);
          --mt-text: #1f1a14;
          --mt-text-soft: #6f6355;
          --mt-accent: #bc6c25;
          --mt-accent-soft: rgba(188, 108, 37, 0.08);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          background: transparent;
          color: var(--mt-text);
          font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        }}
        .mt-js-table {{
          background: var(--mt-panel);
          border: 1px solid var(--mt-border);
          border-radius: 18px;
          overflow: hidden;
        }}
        .mt-js-table__toolbar {{
          display: flex;
          justify-content: space-between;
          gap: 0.75rem;
          align-items: center;
          padding: 0.9rem 1rem;
          border-bottom: 1px solid var(--mt-border);
          background: linear-gradient(180deg, rgba(255,255,255,0.4), rgba(255,255,255,0.1));
        }}
        .mt-js-table__meta {{
          display: flex;
          gap: 0.6rem;
          flex-wrap: wrap;
          align-items: center;
        }}
        .mt-js-table__chip {{
          padding: 0.35rem 0.65rem;
          border-radius: 999px;
          font-size: 12px;
          background: var(--mt-accent-soft);
          color: var(--mt-accent);
          border: 1px solid rgba(188, 108, 37, 0.16);
        }}
        .mt-js-table__search {{
          width: min(320px, 100%);
          border: 1px solid var(--mt-border);
          background: rgba(255, 255, 255, 0.76);
          border-radius: 12px;
          padding: 0.7rem 0.8rem;
          color: var(--mt-text);
          outline: none;
        }}
        .mt-js-table__search:focus {{
          border-color: rgba(188, 108, 37, 0.38);
          box-shadow: 0 0 0 3px rgba(188, 108, 37, 0.1);
        }}
        .mt-js-table__wrap {{
          overflow: auto;
          max-height: 560px;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
          min-width: 720px;
        }}
        thead th {{
          position: sticky;
          top: 0;
          z-index: 1;
          background: rgba(245, 236, 223, 0.98);
          color: var(--mt-text);
          text-align: left;
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 0.8rem 0.9rem;
          border-bottom: 1px solid var(--mt-border);
        }}
        tbody td {{
          padding: 0.82rem 0.9rem;
          border-bottom: 1px solid rgba(108, 76, 39, 0.08);
          color: var(--mt-text);
          font-size: 13px;
          vertical-align: top;
          word-break: break-word;
        }}
        tbody tr:nth-child(even) {{
          background: rgba(255, 255, 255, 0.32);
        }}
        tbody tr:hover {{
          background: rgba(221, 161, 94, 0.09);
        }}
        .mt-js-table__empty {{
          padding: 2rem 1rem;
          text-align: center;
          color: var(--mt-text-soft);
        }}
        .mt-js-table__footer {{
          display: flex;
          justify-content: space-between;
          gap: 0.75rem;
          flex-wrap: wrap;
          align-items: center;
          padding: 0.85rem 1rem;
          color: var(--mt-text-soft);
          border-top: 1px solid var(--mt-border);
          font-size: 12px;
        }}
        @media (max-width: 720px) {{
          .mt-js-table__toolbar {{
            flex-direction: column;
            align-items: stretch;
          }}
          .mt-js-table__search {{
            width: 100%;
          }}
        }}
      </style>
    </head>
    <body>
      <div class="mt-js-table" id="{table_key}">
        <div class="mt-js-table__toolbar">
          <div class="mt-js-table__meta">
            <div class="mt-js-table__chip">HTML + JavaScript grid</div>
            <div class="mt-js-table__chip" id="{table_key}-stats">Loading...</div>
          </div>
          <input class="mt-js-table__search" id="{table_key}-search" type="search" placeholder="Search any value..." />
        </div>
        <div class="mt-js-table__wrap">
          <table>
            <thead id="{table_key}-head"></thead>
            <tbody id="{table_key}-body"></tbody>
          </table>
          <div class="mt-js-table__empty" id="{table_key}-empty" hidden>No rows found.</div>
        </div>
        <div class="mt-js-table__footer">
          <span>{escaped_title}</span>
          <span id="{table_key}-footer">Rendering records...</span>
        </div>
      </div>
      <script>
        const payload = {payload_json};
        const head = document.getElementById(`${{payload.table_key}}-head`);
        const body = document.getElementById(`${{payload.table_key}}-body`);
        const search = document.getElementById(`${{payload.table_key}}-search`);
        const stats = document.getElementById(`${{payload.table_key}}-stats`);
        const footer = document.getElementById(`${{payload.table_key}}-footer`);
        const empty = document.getElementById(`${{payload.table_key}}-empty`);

        const escapeHtml = (value) => String(value ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");

        const renderHead = () => {{
          head.innerHTML = `<tr>${{payload.columns.map((column) => `<th>${{escapeHtml(column)}}</th>`).join("")}}</tr>`;
        }};

        const renderRows = (rows) => {{
          if (!rows.length) {{
            body.innerHTML = "";
            empty.hidden = false;
            footer.textContent = search.value.trim()
              ? `No matches found for "${{search.value.trim()}}".`
              : "No rows available.";
            stats.textContent = `0 / ${{payload.rows.length}} rows`;
            setFrameHeight();
            return;
          }}
          empty.hidden = true;
          body.innerHTML = rows.map((row) => `
            <tr>
              ${{payload.columns.map((column) => `<td>${{escapeHtml(row[column] ?? "")}}</td>`).join("")}}
            </tr>
          `).join("");
          stats.textContent = `${{rows.length}} / ${{payload.rows.length}} rows`;
          footer.textContent = `Columns: ${{payload.columns.length}}`;
          setFrameHeight();
        }};

        const filterRows = () => {{
          const needle = search.value.trim().toLowerCase();
          if (!needle) {{
            renderRows(payload.rows);
            return;
          }}
          const filtered = payload.rows.filter((row) =>
            payload.columns.some((column) => String(row[column] ?? "").toLowerCase().includes(needle))
          );
          renderRows(filtered);
        }};

        const setFrameHeight = () => {{
          const height = Math.min(Math.max(document.body.scrollHeight + 12, 220), 760);
          if (window.parent) {{
            window.parent.postMessage({{
              type: "streamlit:setFrameHeight",
              height,
            }}, "*");
          }}
        }};

        renderHead();
        renderRows(payload.rows);
        search.addEventListener("input", filterRows);
        window.addEventListener("load", setFrameHeight);
        window.addEventListener("resize", setFrameHeight);
      </script>
    </body>
    </html>
    """


def render_table(rows: list[dict], *, caption: str = "") -> None:
    title = caption or "Data table"
    table_key = f"{_slugify(title)}_{next(_TABLE_INSTANCE_COUNTER)}"
    dataframe = _normalize_rows(rows)
    columns = list(dataframe.columns)
    preview_columns = ", ".join(columns[:4]) if columns else "No columns"
    if len(columns) > 4:
        preview_columns = f"{preview_columns} +{len(columns) - 4} more"

    with st.container():
        render_html("<div class='mt-table-template mt-surface'>")
        header_left, header_right = st.columns([3, 2])
        with header_left:
            st.markdown(f"<div class='mt-table-shell__title'>{title}</div>", unsafe_allow_html=True)
            st.markdown("<div class='mt-table-shell__subtitle'>Browse records in a searchable workspace.</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='mt-table-shell__meta'><span>Visible fields</span><strong>{preview_columns}</strong></div>",
                unsafe_allow_html=True,
            )
        with header_right:
            st.markdown(
                (
                    "<div class='mt-table-shell__stats'>"
                    f"<div><span>Rows</span><strong>{len(dataframe)}</strong></div>"
                    f"<div><span>Columns</span><strong>{len(dataframe.columns)}</strong></div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        if dataframe.empty:
            render_empty_state("No rows found.")
            render_html("</div>")
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
            st.markdown(
                f"<div class='mt-table-shell__hint'>Search, scan, and inspect without touching raw JSON.</div>",
                unsafe_allow_html=True,
            )
        table_height = min(max(280, 220 + (min(len(filtered), 10) * 34)), 760)
        components.html(
            _build_html_table(title, filtered, table_key),
            height=table_height,
            scrolling=False,
        )
        render_html("</div>")
