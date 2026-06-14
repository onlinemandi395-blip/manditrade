from __future__ import annotations


class DrivePathResolver:
    def __init__(self, google_drive_service, service, root_folder: dict) -> None:
        self.google_drive_service = google_drive_service
        self.service = service
        self.root_folder = root_folder

    def resolve_folder_path(self, path: str) -> dict:
        current = self.root_folder
        parts = [part for part in path.split("/") if part]
        actual_path = self.root_folder.get("name", "MANDITRADE_DB")
        for part in parts:
            next_folder = self.google_drive_service.find_child(self.service, current["id"], part)
            if not next_folder or next_folder.get("mimeType") != "application/vnd.google-apps.folder":
                return {
                    "logical_path": path,
                    "status": "MISSING",
                    "folder_id": current.get("id", ""),
                    "file_id": "",
                    "actual_path": f"{actual_path}/{part}",
                    "error": "",
                }
            current = next_folder
            actual_path = f"{actual_path}/{part}"
        return {
            "logical_path": path,
            "status": "FOUND",
            "folder_id": current.get("id", ""),
            "file_id": "",
            "actual_path": actual_path,
            "error": "",
        }

    def resolve_file_path(self, path: str) -> dict:
        parts = [part for part in path.split("/") if part]
        folder_path = "/".join(parts[:-1])
        file_name = parts[-1]
        folder_result = self.resolve_folder_path(folder_path) if folder_path else {
            "status": "FOUND",
            "folder_id": self.root_folder.get("id", ""),
            "actual_path": self.root_folder.get("name", "MANDITRADE_DB"),
        }
        if folder_result["status"] != "FOUND":
            folder_result.update({"logical_path": path, "actual_path": f"{folder_result.get('actual_path', '')}/{file_name}"})
            return folder_result
        file_metadata = self.google_drive_service.find_child(self.service, folder_result["folder_id"], file_name)
        actual_path = f"{folder_result['actual_path']}/{file_name}"
        if not file_metadata:
            return {
                "logical_path": path,
                "status": "MISSING",
                "folder_id": folder_result["folder_id"],
                "file_id": "",
                "actual_path": actual_path,
                "error": "",
            }
        return {
            "logical_path": path,
            "status": "FOUND",
            "folder_id": folder_result["folder_id"],
            "file_id": file_metadata.get("id", ""),
            "actual_path": actual_path,
            "error": "",
        }

    def ensure_folder_path(self, path: str) -> dict:
        current = self.root_folder
        parts = [part for part in path.split("/") if part]
        actual_path = self.root_folder.get("name", "MANDITRADE_DB")
        created = False
        for part in parts:
            next_folder = self.google_drive_service.find_child(self.service, current["id"], part)
            if not next_folder:
                next_folder = self.google_drive_service.find_or_create_folder(self.service, part, current["id"])
                created = True
            current = next_folder
            actual_path = f"{actual_path}/{part}"
        return {
            "logical_path": path,
            "status": "CREATED" if created else "FOUND",
            "folder_id": current.get("id", ""),
            "file_id": "",
            "actual_path": actual_path,
            "error": "",
        }

    def ensure_json_file(self, logical_path: str, default_payload: dict) -> dict:
        parts = [part for part in logical_path.split("/") if part]
        folder_path = "/".join(parts[:-1])
        file_name = parts[-1]
        folder_result = self.ensure_folder_path(folder_path)
        file_result = self.resolve_file_path(logical_path)
        if file_result["status"] == "FOUND":
            return file_result
        file_metadata = self.google_drive_service.create_or_update_json_file(
            self.service,
            folder_result["folder_id"],
            file_name,
            default_payload,
        )
        return {
            "logical_path": logical_path,
            "status": "UPDATED" if file_result["status"] == "FOUND" else "CREATED",
            "folder_id": folder_result["folder_id"],
            "file_id": file_metadata.get("id", ""),
            "actual_path": f"{folder_result['actual_path']}/{file_name}",
            "error": "",
        }

    def create_or_update_json_file(self, logical_path: str, payload: dict) -> dict:
        parts = [part for part in logical_path.split("/") if part]
        folder_path = "/".join(parts[:-1])
        file_name = parts[-1]
        folder_result = self.ensure_folder_path(folder_path)
        existing = self.resolve_file_path(logical_path)
        file_metadata = self.google_drive_service.create_or_update_json_file(
            self.service,
            folder_result["folder_id"],
            file_name,
            payload,
        )
        return {
            "logical_path": logical_path,
            "status": "UPDATED" if existing["status"] == "FOUND" else "CREATED",
            "folder_id": folder_result["folder_id"],
            "file_id": file_metadata.get("id", ""),
            "actual_path": f"{folder_result['actual_path']}/{file_name}",
            "error": "",
        }
