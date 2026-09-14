"""Fast, bounded checks before expensive model loading."""

from dataclasses import dataclass
from pathlib import Path

from .errors import MediaValidationError
from .model_catalog import ToolSpec


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    filename: str
    extension: str
    size: int


def _signature_ok(extension: str, head: bytes) -> bool:
    if extension == ".wav":
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    if extension == ".flac":
        return head.startswith(b"fLaC")
    if extension == ".mp3":
        return head.startswith(b"ID3") or head[:1] == b"\xff"
    if extension in {".mp4", ".mov"}:
        return len(head) >= 12 and head[4:8] == b"ftyp"
    if extension == ".webm":
        return head.startswith(b"\x1aE\xdf\xa3")
    if extension == ".avi":
        return len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"AVI "
    return bool(head)


def validate_upload(upload, tool: ToolSpec, ffmpeg_available: bool, max_bytes: int) -> ValidatedUpload:
    filename = (getattr(upload, "filename", "") or "").strip()
    if not filename:
        raise MediaValidationError("لطفاً یک فایل انتخاب کنید.")
    extension = Path(filename).suffix.lower()
    if extension not in tool.accepted_extensions:
        raise MediaValidationError("فرمت این فایل برای ابزار انتخاب‌شده پشتیبانی نمی‌شود.", extension)
    if extension not in tool.direct_extensions and not ffmpeg_available:
        raise MediaValidationError(
            "برای پردازش این فرمت باید FFmpeg نصب باشد.", extension
        )
    stream = getattr(upload, "stream", upload)
    try:
        position = stream.tell()
        data = stream.read(max_bytes + 1)
        stream.seek(position)
    except (AttributeError, OSError) as exc:
        raise MediaValidationError("فایل ورودی خوانده نشد.", str(exc)) from exc
    if not data:
        raise MediaValidationError("فایل انتخاب‌شده خالی است.")
    if len(data) > max_bytes:
        raise MediaValidationError("حجم فایل از محدودیت مجاز بیشتر است.")
    if not _signature_ok(extension, data[:32]):
        raise MediaValidationError("ساختار فایل با پسوند آن هماهنگ نیست.")
    return ValidatedUpload(filename, extension, len(data))

