from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet


class EncryptionService:
    def __init__(self, secret_seed: str, fernet_key: str | None = None) -> None:
        if fernet_key:
            self._fernet = Fernet(fernet_key.encode("utf-8"))
            return
        digest = hashlib.sha256(secret_seed.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    def encrypt_to_file(self, path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.encrypt(value), encoding="utf-8")

    def decrypt_from_file(self, path: Path) -> str:
        return self.decrypt(path.read_text(encoding="utf-8"))
