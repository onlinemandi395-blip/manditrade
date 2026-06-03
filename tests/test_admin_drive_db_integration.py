from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.admin_drive_database_service import AdminDriveDatabaseService
from services.drive_path_service import DrivePathService
from services.file_lock_service import FileLockService
from services.json_service import JsonService
from services.logging_service import LoggingService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService


@dataclass
class _FakeItem:
    id: str
    name: str
    mimeType: str
    parents: list[str]
    trashed: bool = False


class _FakeDriveExecute:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeDriveFilesResource:
    def __init__(self, store: dict[str, _FakeItem]) -> None:
        self.store = store
        self.counter = 1

    def get(self, fileId: str, fields: str | None = None):
        item = self.store[fileId]
        return _FakeDriveExecute({"id": item.id, "name": item.name, "mimeType": item.mimeType, "parents": item.parents, "trashed": item.trashed})

    def list(self, q: str, pageSize: int = 10, fields: str | None = None):
        def _extract(field: str) -> str:
            token = f"{field}='"
            if token not in q:
                return ""
            return q.split(token, 1)[1].split("'", 1)[0]

        name = _extract("name")
        mime_type = _extract("mimeType")
        parent_id = ""
        if " in parents" in q:
            parent_id = q.split("'", 1)[1].split("'", 1)[0]
        matches = []
        for item in self.store.values():
            if item.trashed:
                continue
            if name and item.name != name:
                continue
            if mime_type and item.mimeType != mime_type:
                continue
            if parent_id and parent_id not in item.parents:
                continue
            matches.append({"id": item.id, "name": item.name, "mimeType": item.mimeType, "parents": item.parents})
        return _FakeDriveExecute({"files": matches[:pageSize]})

    def create(self, body: dict, media_body=None, fields: str | None = None):
        item_id = f"fake-{self.counter}"
        self.counter += 1
        item = _FakeItem(
            id=item_id,
            name=body["name"],
            mimeType=body.get("mimeType", "application/json"),
            parents=list(body.get("parents", [])),
        )
        self.store[item_id] = item
        return _FakeDriveExecute({"id": item.id, "name": item.name, "mimeType": item.mimeType, "parents": item.parents})


class _FakeDriveClient:
    def __init__(self) -> None:
        self.store: dict[str, _FakeItem] = {}
        self.files_resource = _FakeDriveFilesResource(self.store)

    def files(self):
        return self.files_resource


class _FakeAuthService:
    def refresh_credentials(self, payload):
        return object()


class _FakeSecurityService:
    def __init__(self, *, token_ready: bool = True) -> None:
        self.admin_token_file = Path("configs/admin_token.enc")
        self._token_ready = token_ready

    def admin_token_ready(self) -> bool:
        return self._token_ready

    def decrypt_refresh_token(self, source: Path | None = None) -> str:
        return "refresh-token"

    def build_runtime_credentials_payload(self, refresh_token: str, access_token: str = "", token_uri: str | None = None, client_id: str | None = None, client_secret: str | None = None) -> dict:
        return {"refresh_token": refresh_token}


class _FakeDriveService:
    def __init__(self, client: _FakeDriveClient, *, use_drive_api: bool = True) -> None:
        self.client = client
        self.use_drive_api = use_drive_api

    def build_drive_client(self, credentials):
        return self.client


def _build_service(tmp_path: Path, *, storage_mode: str = "compatibility") -> AdminDriveDatabaseService:
    json_service = JsonService()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "runtime" / "backups",
        logging_service=LoggingService(tmp_path / "runtime" / "logs"),
        version_history_root=tmp_path / "runtime" / "history",
    )
    drive_path_service = DrivePathService(
        db_root=tmp_path / "data" / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime",
        governance_root=tmp_path / "data" / "governance",
        manufacturers_root=tmp_path / "data" / "manufacturers",
        public_buyers_root=tmp_path / "data" / "public_buyers",
        storage_mode=storage_mode,
        allow_legacy_fallback=True,
    )
    return AdminDriveDatabaseService(
        drive_path_service=drive_path_service,
        safe_drive_write_service=safe_write,
        json_service=json_service,
        runtime_root=tmp_path / "runtime",
        system_config={"storage": {"mode": storage_mode, "admin_drive_db_enabled": True, "admin_db_root_folder_name": "MANDITRADE_DB"}},
        secret_overrides={"google_drive": {"admin_db_root_folder_name": "MANDITRADE_DB"}},
    )


def test_admin_db_root_resolves_from_secret_override(tmp_path):
    service = _build_service(tmp_path)
    resolved = service.resolve_root_config()

    assert resolved["root_folder_name"] == "MANDITRADE_DB"
    assert resolved["source"] == "streamlit_secrets"


def test_admin_drive_bootstrap_dry_run_writes_nothing(tmp_path):
    service = _build_service(tmp_path)
    report = service.bootstrap(dry_run=True)

    assert report["mode"] == "dry_run"
    assert not service.drive_path_service.db_root.exists()


def test_admin_drive_bootstrap_execute_creates_expected_metadata(tmp_path):
    service = _build_service(tmp_path)
    report = service.bootstrap(dry_run=False)

    assert report["mode"] == "execute"
    assert service.drive_path_service.get_registry_path("manufacturers").exists()
    assert service.drive_path_service.get_notification_path("email_queue").exists()


def test_default_json_envelopes_are_valid(tmp_path):
    service = _build_service(tmp_path)
    service.bootstrap(dry_run=False)
    payload = service.json_service.read_json(service.drive_path_service.get_registry_path("manufacturers"), {})

    assert payload["schema_version"] == 1
    assert "manufacturers" in payload


def test_domain_paths_resolve_under_admin_root(tmp_path):
    service = _build_service(tmp_path)
    path = service.drive_path_service.path("orders.marketplace", year_month="2026-06")

    assert "MANDITRADE_DB" in str(path)
    assert "05_orders" in str(path)


def test_canonical_mode_blocks_invalid_admin_drive_db(tmp_path):
    service = _build_service(tmp_path, storage_mode="canonical")

    assert service.canonical_mode_blockers() == [AdminDriveDatabaseService.INVALID_CANONICAL_MESSAGE]


def test_canonical_mode_allows_valid_admin_drive_db(tmp_path):
    service = _build_service(tmp_path, storage_mode="canonical")
    service.bootstrap(dry_run=False)
    service.validate_database_tree(persist=True)

    assert service.canonical_mode_blockers() == []


def test_month_partition_and_media_folder_helpers_work(tmp_path):
    service = _build_service(tmp_path)
    order_path = service.drive_path_service.get_order_path("marketplace", "2026-06")
    media_folder = service.drive_path_service.get_media_folder("payment_proof")

    assert "2026-06" in str(order_path)
    assert media_folder.name == "payment_proofs"


def test_system_health_contains_admin_drive_db_panel():
    content = Path("modules/system/health_dashboard.py").read_text(encoding="utf-8")

    assert "Admin Drive Database" in content
    assert "Validate Admin Drive DB" in content


def test_drive_api_bootstrap_creates_runtime_folder_tree_and_json_refs(tmp_path):
    client = _FakeDriveClient()
    service = _build_service(tmp_path)
    service.drive_service = _FakeDriveService(client)
    service.auth_service = _FakeAuthService()
    service.security_service = _FakeSecurityService(token_ready=True)

    report = service.bootstrap(dry_run=False)

    assert report["runtime"]["runtime_backend"] == "google_drive_api"
    assert report["root"]["exists"] is True
    assert report["root"]["root_folder_id"]
    assert any(item["path"] == "00_config" and item["exists"] for item in report["folder_tree"]["folders"])
    assert any(path.endswith("00_config/system_config.json") for path in report["bootstrap_files"]["created"])


def test_drive_api_runtime_reports_missing_admin_token(tmp_path):
    client = _FakeDriveClient()
    service = _build_service(tmp_path)
    service.drive_service = _FakeDriveService(client)
    service.auth_service = _FakeAuthService()
    service.security_service = _FakeSecurityService(token_ready=False)

    report = service.validate_database_tree(persist=False)

    assert report["runtime"]["drive_api_requested"] is True
    assert report["runtime"]["drive_api_ready"] is False
    assert "Admin runtime token" in report["runtime"]["reason"]
