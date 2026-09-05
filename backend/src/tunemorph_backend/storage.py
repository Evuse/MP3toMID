from abc import ABC, abstractmethod
from pathlib import Path
from shutil import rmtree

from fastapi import UploadFile


class UploadTooLargeError(ValueError):
    pass


class ProjectStorage(ABC):
    @abstractmethod
    def create_project(self, project_id: str) -> None: ...

    @abstractmethod
    async def store_upload(
        self, project_id: str, upload: UploadFile, suffix: str, max_bytes: int
    ) -> tuple[str, int]: ...

    @abstractmethod
    def resolve(self, storage_key: str) -> Path: ...

    @abstractmethod
    def delete_project(self, project_id: str) -> None: ...


class LocalProjectStorage(ProjectStorage):
    directories = ("source", "analysis", "stems", "midi", "preview")

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _project_root(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    def create_project(self, project_id: str) -> None:
        for directory in self.directories:
            (self._project_root(project_id) / directory).mkdir(parents=True, exist_ok=True)

    async def store_upload(
        self, project_id: str, upload: UploadFile, suffix: str, max_bytes: int
    ) -> tuple[str, int]:
        relative = Path("projects") / project_id / "source" / f"audio{suffix}"
        destination = self.root / relative
        temporary = destination.with_suffix(destination.suffix + ".part")
        size = 0
        try:
            with temporary.open("wb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise UploadTooLargeError
                    target.write(chunk)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        return relative.as_posix(), size

    def resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return candidate

    def delete_project(self, project_id: str) -> None:
        rmtree(self._project_root(project_id), ignore_errors=True)
