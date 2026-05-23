from __future__ import annotations

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

from services.encryption_service import EncryptionService

SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"
TOKEN_PATH = BASE_DIR / "configs" / "admin_token.enc"
REQUIRED_SCOPES = [
    "openid",
    "email",
    "profile",
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


def main() -> None:
    secrets = load_secrets()
    client_id = require_value(secrets, "google", "client_id")
    client_secret = require_value(secrets, "google", "client_secret")
    redirect_uri = require_value(secrets, "google", "redirect_uri")
    admin_email = require_value(secrets, "admin", "admin_email")
    fernet_key = require_value(secrets, "security", "fernet_key")

    print("Starting MandiTrade admin token provisioning.")
    print("A browser window will open for Google sign-in and consent.")
    credentials = run_local_oauth(client_id, client_secret, redirect_uri)
    verification = verify_admin_credentials(credentials, admin_email)

    encryption_service = EncryptionService(secret_seed="MandiTrade", fernet_key=fernet_key)
    encryption_service.encrypt_to_file(TOKEN_PATH, credentials.refresh_token)

    # Post-write verification without exposing token content.
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
    oauth_service = build("oauth2", "v2", credentials=verification_credentials)
    profile = oauth_service.userinfo().get().execute()
    owner_email = str(profile.get("email", "")).strip().lower()
    if owner_email != admin_email.strip().lower():
        fail("Provisioned token owner does not match the configured admin email.")
    build("drive", "v3", credentials=verification_credentials)
    build("gmail", "v1", credentials=verification_credentials)

    print("Admin token provisioned successfully")
    print(f"Provisioned owner: {verification['owner_email']}")
    print(f"Token file written to: {TOKEN_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Provisioning cancelled.")
        sys.exit(1)
