from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path

class StorageAdapter(ABC):
    @abstractmethod
    def read(self, path: Path) -> dict[str, Any]:
        pass

    @abstractmethod
    def write(self, path: Path, payload: dict[str, Any], schema_name: str | None = None) -> None:
        pass

    @abstractmethod
    def lock(self, path: Path) -> Any:
        pass

    @abstractmethod
    def unlock(self, path: Path, lock_context: Any) -> None:
        pass

    @abstractmethod
    def backup(self, path: Path) -> Path:
        pass

    @abstractmethod
    def restore(self, paths: list[Path]) -> None:
        pass

    @abstractmethod
    def list_files(self, prefix_path: Path, pattern: str) -> list[Path]:
        pass

    @abstractmethod
    def exists(self, path: Path) -> bool:
        pass