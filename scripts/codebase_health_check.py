from __future__ import annotations

import ast
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TARGET_DIRS = ["modules", "services", "components", "utils", "bootstrap", "scripts"]
ROLE_LITERALS = {"platform_admin", "manufacturer", "mahajan", "public_buyer", "worker", "pending_user"}
JSON_WRITE_MARKERS = ["write_text(", ".write_json(", "json.dump(", "json.dumps("]
MANUAL_PAGE_TITLE_MARKERS = ['st.title(', 'st.header(']
INLINE_STYLE_MARKER = 'style="'


def _python_files() -> list[Path]:
    files: list[Path] = []
    for folder in TARGET_DIRS:
        root = BASE_DIR / folder
        if root.exists():
            files.extend(root.rglob("*.py"))
    return [path for path in files if "runtime" not in path.parts and "__pycache__" not in path.parts]


def _unused_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    imported: dict[str, str] = {}
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                imported[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Name):
            used.add(node.id)
    return [name for name in imported if name not in used and not name.startswith("_")]


def _hardcoded_roles(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.as_posix().endswith("constants/roles.py"):
        return []
    found = []
    for role in ROLE_LITERALS:
        if f'"{role}"' in text or f"'{role}'" in text:
            found.append(role)
    return found


def _bypass_json_write(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    flags: list[str] = []
    for marker in JSON_WRITE_MARKERS:
        if marker in text and "safe_drive_write_service" not in text:
            flags.append(marker.strip("("))
    return flags


def _ui_consistency_flags(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    return {
        "manual_page_titles": any(marker in text for marker in MANUAL_PAGE_TITLE_MARKERS),
        "raw_large_html_cards": "unsafe_allow_html=True" in text and "mt-card-grid" in text,
        "repeated_table_pattern": "render_filter_bar(" in text and "st.dataframe(" in text,
        "repeated_status_chip_code": "mt-badge mt-badge-" in text and "render_status_chip" not in text,
        "direct_inline_color_styles": INLINE_STYLE_MARKER in text and ("color:" in text or "background:" in text),
        "raw_feedback_banners": "st.success(" in text or "st.error(" in text or "st.warning(" in text,
        "direct_exception_rendering": "str(exc)" in text and ("st.error(" in text or "st.code(" in text),
        "duplicate_search_bars": text.count("text_input(") >= 2 and "search" in text.lower(),
    }


def _route_names() -> list[str]:
    route_registry = BASE_DIR / "bootstrap" / "route_registry.py"
    text = route_registry.read_text(encoding="utf-8")
    names: list[str] = []
    for quote in ('"', "'"):
        for role in ROLE_LITERALS:
            pass
    for line in text.splitlines():
        if '"' in line and "{" in line and ":" not in line:
            continue
    # lightweight parse from ROUTE_GROUPS set literals
    try:
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "ROUTE_GROUPS" and isinstance(node.value, ast.Dict):
                        for value in node.value.values:
                            if isinstance(value, ast.Set):
                                for elt in value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        names.append(elt.value)
    except SyntaxError:
        return []
    return names


def _config_files() -> list[str]:
    config_dir = BASE_DIR / "configs"
    return sorted(path.name for path in config_dir.glob("*.json")) if config_dir.exists() else []


def build_report() -> dict:
    files = _python_files()
    oversized = []
    unused_imports: dict[str, list[str]] = {}
    hardcoded_roles: dict[str, list[str]] = {}
    bypass_json_writes: dict[str, list[str]] = {}
    manual_page_title_files: list[str] = []
    raw_large_html_card_files: list[str] = []
    repeated_table_pattern_files: list[str] = []
    repeated_status_chip_files: list[str] = []
    direct_inline_color_style_files: list[str] = []
    raw_feedback_banner_files: list[str] = []
    direct_exception_rendering_files: list[str] = []
    duplicate_search_bar_files: list[str] = []

    for path in files:
        rel = path.relative_to(BASE_DIR).as_posix()
        line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        if line_count >= 400:
            oversized.append({"path": rel, "lines": line_count})
        unused = _unused_imports(path)
        if unused:
            unused_imports[rel] = unused
        roles = _hardcoded_roles(path)
        if roles:
            hardcoded_roles[rel] = sorted(set(roles))
        writes = _bypass_json_write(path)
        if writes and "tests/" not in rel:
            bypass_json_writes[rel] = sorted(set(writes))
        ui_flags = _ui_consistency_flags(path)
        if ui_flags["manual_page_titles"]:
            manual_page_title_files.append(rel)
        if ui_flags["raw_large_html_cards"]:
            raw_large_html_card_files.append(rel)
        if ui_flags["repeated_table_pattern"]:
            repeated_table_pattern_files.append(rel)
        if ui_flags["repeated_status_chip_code"]:
            repeated_status_chip_files.append(rel)
        if ui_flags["direct_inline_color_styles"]:
            direct_inline_color_style_files.append(rel)
        if ui_flags["raw_feedback_banners"]:
            raw_feedback_banner_files.append(rel)
        if ui_flags["direct_exception_rendering"]:
            direct_exception_rendering_files.append(rel)
        if ui_flags["duplicate_search_bars"]:
            duplicate_search_bar_files.append(rel)

    route_names = _route_names()
    route_counter = Counter(route_names)
    duplicate_routes = sorted(name for name, count in route_counter.items() if count > 1)

    service_files = sorted((BASE_DIR / "services").glob("*.py"))
    service_names = {path.stem.replace("_service", "") for path in service_files}
    test_files = {path.stem for path in (BASE_DIR / "tests").glob("test_*.py")}
    missing_test_hints = sorted(
        path.name
        for path in service_files
        if path.stem not in {"__init__"}
        and not any(path.stem.replace("_service", "") in test_name for test_name in test_files)
        and path.stat().st_size > 0
    )[:25]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "python_files_scanned": len(files),
        "oversized_files": oversized,
        "unused_imports": unused_imports,
        "duplicate_route_names": duplicate_routes,
        "hardcoded_role_string_files": hardcoded_roles,
        "direct_json_write_bypass_candidates": bypass_json_writes,
        "manual_page_title_candidates": sorted(manual_page_title_files),
        "raw_large_html_card_candidates": sorted(raw_large_html_card_files),
        "repeated_table_pattern_candidates": sorted(repeated_table_pattern_files),
        "repeated_status_chip_candidates": sorted(repeated_status_chip_files),
        "direct_inline_color_style_candidates": sorted(direct_inline_color_style_files),
        "raw_feedback_banner_candidates": sorted(raw_feedback_banner_files),
        "direct_exception_rendering_candidates": sorted(direct_exception_rendering_files),
        "duplicate_search_bar_candidates": sorted(duplicate_search_bar_files),
        "config_files_present": _config_files(),
        "missing_test_hints": missing_test_hints,
        "notes": [
            "This report is heuristic and intentionally conservative.",
            "Compatibility-safe legacy paths may appear in findings and should be evaluated manually before removal.",
        ],
    }


def main() -> Path:
    report = build_report()
    reports_dir = BASE_DIR / "runtime" / "health_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = reports_dir / f"codebase_health_{stamp}.json"
    latest = reports_dir / "latest_codebase_health.json"
    payload = json.dumps(report, indent=2, ensure_ascii=True)
    target.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    print(str(target))
    return target


if __name__ == "__main__":
    main()
