"""Translate friendly web requests into existing ClearVoice calls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import MediaValidationError, ProcessingError
from .model_catalog import get_model_spec, get_tool_spec
from .validation import validate_upload


@dataclass(frozen=True, slots=True)
class OutputArtifact:
    filename: str
    label_fa: str
    media_kind: str


@dataclass(frozen=True, slots=True)
class JobResult:
    job_id: str
    tool_slug: str
    tool_title_fa: str
    model_name: str
    model_label_fa: str
    input_name: str
    input_size: int
    outputs: tuple[OutputArtifact, ...]
    bundle_name: str | None
    notice_fa: str | None


class ProcessingService:
    def __init__(self, job_store, model_manager, ffmpeg_available: bool, max_upload_bytes: int):
        self.job_store = job_store
        self.model_manager = model_manager
        self.ffmpeg_available = ffmpeg_available
        self.max_upload_bytes = max_upload_bytes

    def _select_model(self, tool, requested: str | None) -> str:
        if len(tool.model_names) == 1:
            return tool.model_names[0]
        if not requested or requested not in tool.model_names:
            raise MediaValidationError("لطفاً یکی از مدل‌های مجاز این ابزار را انتخاب کنید.")
        return requested

    def process(self, tool_slug: str, model_name: str | None, upload) -> JobResult:
        try:
            tool = get_tool_spec(tool_slug)
        except KeyError as exc:
            raise MediaValidationError("ابزار انتخاب‌شده معتبر نیست.") from exc
        selected = self._select_model(tool, model_name)
        validated = validate_upload(
            upload, tool, self.ffmpeg_available, self.max_upload_bytes
        )
        job = self.job_store.create()
        input_path = self.job_store.save_upload(job, upload.stream, validated.filename)
        try:
            notice = self.model_manager.run(selected, input_path, job.output_dir)
        except Exception:
            raise
        files = [path for path in job.output_dir.rglob("*") if path.is_file()]
        if not files:
            raise ProcessingError("مدل پردازش را تمام کرد اما فایل خروجی ساخته نشد.")
        names = self.job_store.register_outputs(job.id, files)
        artifacts: list[OutputArtifact] = []
        for index, name in enumerate(names):
            if tool.output_kind == "multi_audio":
                label = "گوینده اول" if index == 0 else "گوینده دوم" if index == 1 else f"خروجی {index + 1}"
            elif tool.output_kind == "single_audio":
                label = "صدای پردازش‌شده"
            else:
                label = "خروجی ویدئویی" if Path(name).suffix.lower() in {".mp4", ".mov", ".avi", ".webm"} else "صدای گوینده هدف"
            media_kind = "video" if Path(name).suffix.lower() in {".mp4", ".mov", ".avi", ".webm"} else "audio"
            artifacts.append(OutputArtifact(name, label, media_kind))
        bundle_name = None
        if len(artifacts) > 1:
            bundle_name = self.job_store.bundle_outputs(job.id).name
        model = get_model_spec(selected)
        result = JobResult(
            job.id, tool.slug, tool.title_fa, selected, model.label_fa,
            validated.filename, validated.size, tuple(artifacts), bundle_name, notice,
        )
        self.job_store.update_result(job.id, {
            "tool_slug": result.tool_slug,
            "tool_title_fa": result.tool_title_fa,
            "model_name": result.model_name,
            "model_label_fa": result.model_label_fa,
            "input_name": result.input_name,
            "input_size": result.input_size,
            "artifacts": [artifact.__dict__ if hasattr(artifact, "__dict__") else {
                "filename": artifact.filename,
                "label_fa": artifact.label_fa,
                "media_kind": artifact.media_kind,
            } for artifact in result.outputs],
            "bundle_name": result.bundle_name,
            "notice_fa": result.notice_fa,
        })
        return result

    def load_result(self, job_id: str) -> JobResult:
        data = self.job_store.read_metadata(job_id)
        required = ("tool_slug", "tool_title_fa", "model_name", "model_label_fa", "input_name")
        if not all(key in data for key in required):
            raise ProcessingError("اطلاعات نتیجه کامل نیست.")
        artifacts = tuple(OutputArtifact(**item) for item in data.get("artifacts", []))
        return JobResult(
            job_id, data["tool_slug"], data["tool_title_fa"], data["model_name"],
            data["model_label_fa"], data["input_name"], data.get("input_size", 0),
            artifacts, data.get("bundle_name"), data.get("notice_fa"),
        )

