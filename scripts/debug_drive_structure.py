from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import sys
import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.drive_path_resolver import DrivePathResolver
from services.google_drive_service import GoogleDriveService
from services.required_drive_files import build_required_drive_files


def load_secrets(repo_root: Path) -> dict:
    secrets_path = repo_root / ".streamlit" / "secrets.toml"
    return tomllib.loads(secrets_path.read_text(encoding="utf-8"))


def main() -> None:
    repo_root = REPO_ROOT
    runtime_token_path = repo_root / "runtime" / "oauth" / "admin_user_token.json"
    if not runtime_token_path.exists():
        raise FileNotFoundError("Admin OAuth token file missing: runtime/oauth/admin_user_token.json")
    token = json.loads(runtime_token_path.read_text(encoding="utf-8"))
    secrets = load_secrets(repo_root)

    google_drive = dict(secrets.get("google_drive", {}))
    platform = dict(secrets.get("platform", {}))
    root_folder_id = str(google_drive.get("root_folder_id", "")).strip()
    root_folder_name = str(google_drive.get("root_folder_name", "") or "MANDITRADE_DB").strip()

    drive_service = GoogleDriveService(runtime_token_path)
    service = drive_service.build_drive_client_from_user_oauth(token)
    if root_folder_id:
        root = service.files().get(fileId=root_folder_id, fields="id,name,mimeType").execute()
    else:
        root = drive_service.find_child(service, "root", root_folder_name)
        if not root:
            raise FileNotFoundError(f"Drive root folder not found: {root_folder_name}")

    resolver = DrivePathResolver(drive_service, service, root)
    required = build_required_drive_files(
        str(platform.get("primary_admin_email", "")).strip().lower(),
        str(platform.get("primary_admin_name", "") or "Primary Admin").strip(),
    )
    report_rows = [resolver.resolve_file_path(item["logical_path"]) for item in required]

    print(f"{root['name']}/")
    printed_folders: set[str] = set()
    for row in report_rows:
        parts = row["logical_path"].split("/")
        prefix = root["name"]
        indent = "  "
        for folder in parts[:-1]:
            prefix = f"{prefix}/{folder}"
            if prefix not in printed_folders:
                print(f"{indent}{folder}/")
                printed_folders.add(prefix)
            indent += "  "
        print(f"{indent}{parts[-1]} [{row['status']}]")

    out_dir = repo_root / "runtime" / "drive_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"drive_structure_{timestamp}.json"
    out_path.write_text(json.dumps({"generated_at": datetime.now(UTC).isoformat(), "root_folder": root, "required_files": report_rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
