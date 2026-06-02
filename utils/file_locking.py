from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(target: Path, content: str, *, encoding: str = "utf-8") -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_suffix(f"{target.suffix}.tmp")
    with temp_path.open("w", encoding=encoding) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, target)
