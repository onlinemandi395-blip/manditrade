from __future__ import annotations

import csv
import io
import json
from typing import Any


def export_rows_to_csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    headers: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    return stream.getvalue().encode("utf-8")


def export_rows_to_json_bytes(rows: list[dict[str, Any]]) -> bytes:
    return json.dumps(rows, indent=2, ensure_ascii=True).encode("utf-8")
