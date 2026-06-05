from __future__ import annotations

import argparse
import os
import sys
import tomllib
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.drive_config_service import DriveConfigService
from services.encryption_service import EncryptionService

SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"
TOKEN_PATH = BASE_DIR / "runtime" / "tokens" / "admin_token.enc"
DEFAULT_LOCAL_REDIRECT_URI = "http://localhost:8501"
REQUIRED_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
]


def fail(message: str) -> None:
    print(f"Provisioning failed: {message}")
    raise SystemExit(1)


def load_secrets() -> dict:
    if not SECRETS_PATH.exists():
        fail("Missing .streamlit/secrets.toml")
    with SECRETS_PATH.open("rb") as handle:
        return tomllib.load(handle)


def load_local_oauth_redirect() -> str:
    try:
        oauth_config = DriveConfigService().load_json("oauth_config.json")
    except Exception:
        return DEFAULT_LOCAL_REDIRECT_URI
    redirect_uri = str(oauth_config.get("google_oauth", {}).get("redirect_uri", "")).strip()
    parsed = urlparse(redirect_uri)
    if parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port:
        return redirect_uri
    return DEFAULT_LOCAL_REDIRECT_URI


def require_value(source: dict, section: str, field: str) -> str:
    value = str(source.get(section, {}).get(field, "")).strip()
    if not value:
        fail(f"Missing required secret: [{section}] {field}")
    return value


def build_client_config(client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return {
        "web": {
            "client_id": client_id,
            "project_id": "manditrade-local-provisioning",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": client_secret,
            "redirect_uris": [redirect_uri],
        }
    }


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    callback_url: str | None = None
    callback_error: str | None = None
    expected_path: str = "/"

    def do_GET(self) -> None:  # noqa: N802
        request_path = self.path.split("?", 1)[0] or "/"
        if request_path != self.expected_path:
            self.send_response(404)
            self.end_headers()
            return
        self.__class__.callback_url = f"http://{self.headers['Host']}{self.path}"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>MandiTrade admin token provisioning completed.</h2><p>You can close this tab.</p></body></html>"
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run_local_oauth(client_id: str, client_secret: str, redirect_uri: str):
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1"}:
        fail("Redirect URI must be a local loopback URI for provisioning.")
    if not parsed.port:
        fail("Redirect URI must include an explicit local port.")
    if parsed.scheme == "http":
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
    flow = Flow.from_client_config(
        build_client_config(client_id, client_secret, redirect_uri),
        scopes=REQUIRED_SCOPES,
        redirect_uri=redirect_uri,
    )
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    callback_path = parsed.path or "/"
    OAuthCallbackHandler.callback_url = None
    OAuthCallbackHandler.callback_error = None
    OAuthCallbackHandler.expected_path = callback_path
    server = HTTPServer((parsed.hostname, parsed.port), OAuthCallbackHandler)
    server.timeout = 300
    print("Opening a browser window for MandiTrade admin token provisioning.")
    print(f"Using redirect URI: {redirect_uri}")
    webbrowser.open(authorization_url, new=1, autoraise=True)
    while OAuthCallbackHandler.callback_url is None:
        server.handle_request()
    server.server_close()
    flow.fetch_token(authorization_response=OAuthCallbackHandler.callback_url)
    return flow.credentials


def verify_admin_credentials(credentials, admin_email: str) -> dict:
    if not credentials.refresh_token:
        fail("OAuth flow completed but no refresh token was returned.")
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    oauth_service = build("oauth2", "v2", credentials=credentials)
    profile = oauth_service.userinfo().get().execute()
    owner_email = str(profile.get("email", "")).strip().lower()
    if owner_email != admin_email.strip().lower():
        fail("Signed-in Google account does not match the configured admin email.")
    build("drive", "v3", credentials=credentials)
    build("gmail", "v1", credentials=credentials)
    return {
        "owner_email": owner_email,
        "scopes": list(credentials.scopes or []),
    }


def mask_token(token: str) -> str:
    if len(token) <= 12:
        return "*" * len(token)
    return f"{token[:6]}...{token[-6:]}"


def render_section(name: str, values: dict[str, str]) -> str:
    lines = [f"[{name}]"]
    for key, value in values.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}="{escaped}"')
    return "\n".join(lines)


def upsert_section(content: str, section_name: str, values: dict[str, str]) -> str:
    lines = content.splitlines()
    start = None
    end = None
    for index, line in enumerate(lines):
        if line.strip() == f"[{section_name}]":
            start = index
            end = len(lines)
            for probe in range(index + 1, len(lines)):
                stripped = lines[probe].strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    end = probe
                    break
            break
    section_text = render_section(section_name, values).splitlines()
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(section_text)
    else:
        lines[start:end] = section_text
    return "\n".join(lines) + "\n"


def write_refresh_token_to_secrets(refresh_token: str) -> None:
    content = SECRETS_PATH.read_text(encoding="utf-8") if SECRETS_PATH.exists() else ""
    existing_secrets = load_secrets()
    content = upsert_section(
        content,
        "admin",
        {
            "admin_email": require_value(existing_secrets, "admin", "admin_email"),
            "admin_refresh_token": refresh_token,
        },
    )
    google_drive = existing_secrets.get("google_drive", {})
    content = upsert_section(
        content,
        "google_drive",
        {
            "admin_db_root_folder_name": str(google_drive.get("admin_db_root_folder_name", "MANDITRADE_DB") or "MANDITRADE_DB"),
            "admin_db_root_folder_id": str(google_drive.get("admin_db_root_folder_id", "") or ""),
        },
    )
    SECRETS_PATH.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision MandiTrade admin Google refresh token.")
    parser.add_argument(
        "--redirect-uri",
        default="",
        help="Local loopback redirect URI to use for OAuth provisioning. Example: http://localhost:8501",
    )
    parser.add_argument(
        "--write-secrets",
        action="store_true",
        help="Write the refresh token into .streamlit/secrets.toml as [admin].admin_refresh_token.",
    )
    parser.add_argument(
        "--write-encrypted-file",
        action="store_true",
        help="Also write the refresh token to runtime/tokens/admin_token.enc for compatibility.",
    )
    parser.add_argument(
        "--print-token",
        action="store_true",
        help="Print the full refresh token after provisioning.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    secrets = load_secrets()
    client_id = require_value(secrets, "google", "client_id")
    client_secret = require_value(secrets, "google", "client_secret")
    admin_email = require_value(secrets, "admin", "admin_email")
    fernet_key = require_value(secrets, "security", "fernet_key")
    redirect_uri = args.redirect_uri.strip() or load_local_oauth_redirect()

    print("Starting MandiTrade admin token provisioning.")
    print("A browser window will open for Google sign-in and consent.")
    print(f"Configured admin email: {admin_email}")
    print("")
    print("Important:")
    print(f"- Make sure this redirect URI is added in Google Cloud Console: {redirect_uri}")
    print("- Sign in with the same Gmail that owns or can access the MANDITRADE_DB folder.")
    credentials = run_local_oauth(client_id, client_secret, redirect_uri)
    verification = verify_admin_credentials(credentials, admin_email)

    if args.write_secrets:
        write_refresh_token_to_secrets(credentials.refresh_token)

    if args.write_encrypted_file:
        encryption_service = EncryptionService(secret_seed="MandiTrade", fernet_key=fernet_key)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        encryption_service.encrypt_to_file(TOKEN_PATH, credentials.refresh_token)

        decrypted_refresh_token = encryption_service.decrypt_from_file(TOKEN_PATH)
        if decrypted_refresh_token != credentials.refresh_token:
            fail("Encrypted token verification failed after write.")
        verification_credentials = Credentials(
            token=None,
            refresh_token=decrypted_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=REQUIRED_SCOPES,
        )
        verification_credentials.refresh(Request())
        build("drive", "v3", credentials=verification_credentials)
        build("gmail", "v1", credentials=verification_credentials)

    print("")
    print("Admin refresh token captured successfully.")
    print(f"Provisioned owner: {verification['owner_email']}")
    print(f"Scopes granted: {len(verification['scopes'])}")
    print(f"Masked refresh token: {mask_token(credentials.refresh_token)}")
    if args.print_token:
        print(f"Refresh token: {credentials.refresh_token}")
    if args.write_secrets:
        print(f"Updated secrets file: {SECRETS_PATH}")
    if args.write_encrypted_file:
        print(f"Encrypted token file written to: {TOKEN_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Provisioning cancelled.")
        sys.exit(1)
