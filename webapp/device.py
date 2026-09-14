"""Hardware selection that is easy to unit test."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceChoice:
    name: str
    label_fa: str

    def torch_device(self, torch_module):
        return torch_module.device(self.name)


LABELS = {
    "cuda": "پردازنده گرافیکی NVIDIA (CUDA)",
    "mps": "پردازنده گرافیکی Apple (MPS)",
    "cpu": "پردازنده اصلی (CPU)",
}


def _mps_available(torch_module) -> bool:
    backend = getattr(getattr(torch_module, "backends", None), "mps", None)
    return bool(
        backend
        and getattr(backend, "is_available", lambda: False)()
        and getattr(backend, "is_built", lambda: False)()
    )


def choose_device(torch_module, override: str = "auto") -> DeviceChoice:
    requested = (override or "auto").strip().lower()
    if requested not in {"auto", "cuda", "mps", "cpu"}:
        raise ValueError("مقدار انتخاب دستگاه معتبر نیست.")
    cuda_available = bool(torch_module.cuda.is_available())
    mps_available = _mps_available(torch_module)
    if requested == "auto":
        name = "cuda" if cuda_available else "mps" if mps_available else "cpu"
    elif requested == "cuda" and not cuda_available:
        raise ValueError("دستگاه CUDA در دسترس نیست.")
    elif requested == "mps" and not mps_available:
        raise ValueError("دستگاه MPS در دسترس نیست.")
    else:
        name = requested
    return DeviceChoice(name, LABELS[name])


def is_mps_fallback_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    backend_marker = "mps" in message or "metal" in message
    failure_marker = any(word in message for word in (
        "not implemented", "unsupported", "does not support", "backend"
    ))
    return backend_marker and failure_marker

