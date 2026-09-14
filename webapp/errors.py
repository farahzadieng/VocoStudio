"""User-facing error types with Persian messages."""


class WebAppError(Exception):
    status_code = 400

    def __init__(self, message_fa: str, technical_detail: str | None = None):
        super().__init__(message_fa)
        self.message_fa = message_fa
        self.technical_detail = technical_detail


class CheckpointError(WebAppError):
    status_code = 503


class MediaValidationError(WebAppError):
    status_code = 400


class ProcessingError(WebAppError):
    status_code = 500


class JobNotFoundError(WebAppError):
    status_code = 404

