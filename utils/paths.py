from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIGS_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
MANUFACTURERS_DIR = DATA_DIR / "manufacturers"
STREAMLIT_DIR = BASE_DIR / ".streamlit"
GOVERNANCE_DIR = DATA_DIR / "governance"
APP_RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_TOKENS_DIR = APP_RUNTIME_DIR / "tokens"
RUNTIME_BACKUPS_DIR = APP_RUNTIME_DIR / "backups"
RUNTIME_LOGS_DIR = APP_RUNTIME_DIR / "logs"
RUNTIME_VERSION_HISTORY_DIR = APP_RUNTIME_DIR / "version_history"
RUNTIME_DEAD_LETTER_DIR = APP_RUNTIME_DIR / "dead_letter"
RUNTIME_METRICS_DIR = APP_RUNTIME_DIR / "metrics"
RUNTIME_EVENTS_INDEX_DIR = APP_RUNTIME_DIR / "events" / "index"
RUNTIME_RECOVERY_DIR = APP_RUNTIME_DIR / "recovery"
