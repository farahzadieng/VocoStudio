"""Isolated local job storage with output allowlisting."""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .errors import JobNotFoundError


@dataclass(frozen=True, slots=True)
class JobPaths:
    id: str
    root: Path
    input_dir: Path
    output_dir: Path
    metadata_path: Path


class JobStore:
    def __init__(self, runtime_root: Path):
        self.runtime_root = Path(runtime_root).resolve()
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def _paths(self, job_id: str) -> JobPaths:
        if not job_id or any(char not in "0123456789abcdef-" for char in job_id.lower()):
            raise JobNotFoundError("نتیجه موردنظر پیدا نشد.")
        root = (self.runtime_root / job_id).resolve()
        if self.runtime_root not in root.parents:
            raise JobNotFoundError("نتیجه موردنظر پیدا نشد.")
        return JobPaths(job_id, root, root / "input", root / "output", root / "job.json")

    def create(self) -> JobPaths:
        job = self._paths(str(uuid.uuid4()))
        job.input_dir.mkdir(parents=True)
        job.output_dir.mkdir()
        self.write_metadata(job.id, {"id": job.id, "outputs": []})
        return job

    def write_metadata(self, job_id: str, data: dict) -> None:
        job = self._paths(job_id)
        job.root.mkdir(parents=True, exist_ok=True)
        temporary = job.metadata_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, job.metadata_path)

    def read_metadata(self, job_id: str) -> dict:
        job = self._paths(job_id)
        if not job.metadata_path.is_file():
            raise JobNotFoundError("نتیجه موردنظر پیدا نشد.")
        try:
            return json.loads(job.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise JobNotFoundError("اطلاعات نتیجه قابل خواندن نیست.", str(exc)) from exc

    def save_upload(self, job: JobPaths, stream, original_name: str) -> Path:
        extension = Path(original_name).suffix.lower()
        destination = job.input_dir / f"{uuid.uuid4().hex}{extension}"
        stream.seek(0)
        with destination.open("wb") as output:
            shutil.copyfileobj(stream, output)
        stream.seek(0)
        return destination

    def register_outputs(self, job_id: str, paths: list[Path]) -> tuple[str, ...]:
        job = self._paths(job_id)
        output_root = job.output_dir.resolve()
        registered: dict[str, str] = {}
        for path in sorted((Path(item).resolve() for item in paths), key=lambda item: item.name):
            if output_root not in path.parents or not path.is_file():
                raise ValueError("Output must be a file inside the job output directory")
            name = path.name
            if name in registered:
                name = f"{path.parent.name}-{name}"
            registered[name] = str(path.relative_to(job.root))
        metadata = self.read_metadata(job_id)
        metadata["outputs"] = [{"name": name, "path": value} for name, value in registered.items()]
        self.write_metadata(job_id, metadata)
        return tuple(registered)

    def update_result(self, job_id: str, values: dict) -> dict:
        metadata = self.read_metadata(job_id)
        metadata.update(values)
        self.write_metadata(job_id, metadata)
        return metadata

    def resolve_output(self, job_id: str, filename: str) -> Path:
        if Path(filename).name != filename:
            raise KeyError(filename)
        job = self._paths(job_id)
        metadata = self.read_metadata(job_id)
        matches = [item for item in metadata.get("outputs", []) if item.get("name") == filename]
        if len(matches) != 1:
            raise KeyError(filename)
        path = (job.root / matches[0]["path"]).resolve()
        if job.output_dir.resolve() not in path.parents or not path.is_file():
            raise KeyError(filename)
        return path

    def bundle_outputs(self, job_id: str) -> Path:
        job = self._paths(job_id)
        metadata = self.read_metadata(job_id)
        bundle = job.root / "clearvoice-results.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in metadata.get("outputs", []):
                path = self.resolve_output(job_id, item["name"])
                archive.write(path, item["name"])
        return bundle

    def resolve_bundle(self, job_id: str) -> Path:
        bundle = self._paths(job_id).root / "clearvoice-results.zip"
        if not bundle.is_file():
            raise KeyError(job_id)
        return bundle

    def cleanup_stale(self, retention_hours: int) -> tuple[str, ...]:
        cutoff = time.time() - retention_hours * 3600
        removed: list[str] = []
        for child in self.runtime_root.iterdir():
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child)
                removed.append(child.name)
        return tuple(removed)

