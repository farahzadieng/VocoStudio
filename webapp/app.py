"""Flask application factory and local-only routes."""

from __future__ import annotations

import hmac
import logging
import secrets
from pathlib import Path

from flask import (
    Flask, abort, jsonify, redirect, render_template, request,
    send_file, session, url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge

from .config import AppConfig
from .errors import JobNotFoundError, MediaValidationError, WebAppError
from .model_catalog import MODEL_CATALOG, TOOL_CATALOG, get_tool_spec


LOGGER = logging.getLogger("clearvoice.webapp")


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(24)
        session["csrf_token"] = token
    return token


def _valid_csrf(value: str | None) -> bool:
    expected = session.get("csrf_token", "")
    return bool(value and expected and hmac.compare_digest(value, expected))


def create_app(
    config: AppConfig | None = None,
    processing_service=None,
    job_store=None,
    diagnostics: dict | None = None,
) -> Flask:
    runtime = config or AppConfig.discover()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        MAX_CONTENT_LENGTH=runtime.max_upload_bytes,
        SEND_FILE_MAX_AGE_DEFAULT=0,
        JSON_AS_ASCII=False,
    )
    app.extensions["clearvoice_service"] = processing_service
    app.extensions["clearvoice_store"] = job_store
    app.extensions["clearvoice_diagnostics"] = diagnostics or {}

    if job_store is not None:
        job_store.cleanup_stale(runtime.retention_hours)

    @app.context_processor
    def inject_globals():
        return {"csrf_token": _csrf_token, "model_catalog": MODEL_CATALOG}

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            title="استودیوی صدای شفاف",
            tools=TOOL_CATALOG,
            diagnostics=app.extensions["clearvoice_diagnostics"],
        )

    @app.get("/tools/<slug>")
    def tool_page(slug: str):
        try:
            tool = get_tool_spec(slug)
        except KeyError:
            abort(404)
        status = app.extensions["clearvoice_diagnostics"]
        unavailable = set(status.get("unavailable_models", ()))
        return render_template(
            "tool.html", title=tool.title_fa, tool=tool,
            unavailable_models=unavailable,
        )

    @app.post("/process/<slug>")
    def process(slug: str):
        if not _valid_csrf(request.form.get("csrf_token")):
            raise MediaValidationError("نشست فرم منقضی شده است؛ صفحه را تازه‌سازی کنید.")
        try:
            get_tool_spec(slug)
        except KeyError:
            abort(404)
        upload = request.files.get("media")
        if upload is None:
            raise MediaValidationError("لطفاً یک فایل انتخاب کنید.")
        service = app.extensions.get("clearvoice_service")
        if service is None:
            raise WebAppError("سرویس پردازش آماده نیست.", "Processing service is not configured")
        result = service.process(slug, request.form.get("model_name"), upload)
        return redirect(url_for("result_page", job_id=result.job_id), code=303)

    @app.get("/results/<job_id>")
    def result_page(job_id: str):
        service = app.extensions.get("clearvoice_service")
        if service is None:
            raise JobNotFoundError("نتیجه موردنظر پیدا نشد.")
        result = service.load_result(job_id)
        return render_template("result.html", title="نتیجه پردازش", result=result)

    @app.get("/downloads/<job_id>/<filename>")
    def download_output(job_id: str, filename: str):
        store = app.extensions.get("clearvoice_store")
        if store is None:
            raise JobNotFoundError("فایل خروجی پیدا نشد.")
        try:
            path = store.resolve_output(job_id, filename)
        except KeyError as exc:
            raise JobNotFoundError("فایل خروجی پیدا نشد.") from exc
        return send_file(path, as_attachment=request.args.get("preview") != "1", download_name=filename)

    @app.get("/downloads/<job_id>/bundle")
    def download_bundle(job_id: str):
        store = app.extensions.get("clearvoice_store")
        if store is None:
            raise JobNotFoundError("بسته خروجی پیدا نشد.")
        try:
            path = store.resolve_bundle(job_id)
        except KeyError as exc:
            raise JobNotFoundError("بسته خروجی پیدا نشد.") from exc
        return send_file(path, as_attachment=True, download_name="clearvoice-results.zip")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", **app.extensions["clearvoice_diagnostics"]})

    @app.errorhandler(WebAppError)
    def handle_known_error(exc: WebAppError):
        return render_template(
            "error.html", title="امکان ادامه پردازش نیست",
            message=exc.message_fa, detail=exc.technical_detail,
        ), exc.status_code

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(exc):
        return render_template(
            "error.html", title="حجم فایل زیاد است",
            message="حجم فایل از محدودیت ۵۰۰ مگابایت بیشتر است.", detail=None,
        ), 413

    @app.errorhandler(404)
    def handle_not_found(exc):
        return render_template(
            "error.html", title="صفحه پیدا نشد",
            message="آدرس درخواستی در این برنامه وجود ندارد.", detail=None,
        ), 404

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        if app.testing:
            raise exc
        LOGGER.exception("Unexpected web application error")
        return render_template(
            "error.html", title="پردازش انجام نشد",
            message="یک خطای پیش‌بینی‌نشده رخ داد. جزئیات در پنجره اجرای برنامه ثبت شد.",
            detail=str(exc),
        ), 500

    return app

