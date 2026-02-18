from __future__ import annotations

import os
from pathlib import Path
from flask import Flask, render_template, request, send_file, abort, g

from .utils import now_timestamp_ms, sanitize_filename, project_root
from .db import init_db, connect, get_db_path, create_job, insert_mapping, load_mapping_dict
from .pii_detector import detect
from .tokenizer import anonymize
from .decoder import extract_job_id_from_text, extract_job_id_from_filename, deanonymize
from .hardening import (
    MAX_UPLOAD_BYTES,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    InMemoryRateLimiter,
    extract_client_ip,
    log_event,
    setup_app_logger,
    validate_txt_upload,
)


def create_app() -> Flask:
    root = project_root()
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )

    data_dir = root / "data"
    storage_dir = root / "storage"
    logs_dir = root / "logs"
    for d in (data_dir, storage_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    db_path = get_db_path(data_dir)
    init_db(db_path)
    app_logger = setup_app_logger(logs_dir)
    rate_limiter = InMemoryRateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/encode")
    def encode_route():
        client_ip = extract_client_ip(request)
        g.client_ip = client_ip
        g.route = request.path
        g.job_id = None
        g.file_size = None
        g.entities_found = None

        if not rate_limiter.allow(client_ip):
            abort(429)

        f = request.files.get("file")
        if not f or not f.filename:
            abort(400, "No file uploaded")
        validation_error = validate_txt_upload(f)
        if validation_error:
            abort(400, validation_error)

        original_full = f.filename
        original_safe = sanitize_filename(original_full)
        raw = f.read()
        g.file_size = len(raw)
        if len(raw) > MAX_UPLOAD_BYTES:
            abort(413)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            abort(400, "File must be valid UTF-8 TXT.")

        ts = now_timestamp_ms()
        with connect(db_path) as conn:
            temp_job_id = f"JOB-TEMP-{ts}--{original_full}"
            job_no = create_job(conn, temp_job_id, original_full, original_safe, ts)
            job_id = f"JOB-{job_no:06d}-{ts}--{original_full}"
            g.job_id = job_id
            conn.execute("UPDATE jobs SET job_id=? WHERE job_no=?", (job_id, job_no))
            conn.commit()

            job_dir = storage_dir / job_id
            (job_dir / "input").mkdir(parents=True, exist_ok=True)
            (job_dir / "output").mkdir(parents=True, exist_ok=True)

            input_path = job_dir / "input" / original_safe
            input_path.write_text(text, encoding="utf-8")

            entities = detect(text)
            g.entities_found = len(entities)
            anon_text, mappings = anonymize(text, entities)

            anon_text_with_header = f"## ANON_JOB: {job_id}\n" + anon_text

            for m in mappings:
                insert_mapping(conn, job_id, m.token, m.entity_type, m.original_value)
            conn.commit()

            out_name = f"{Path(original_safe).stem}__ANON__{job_id}{Path(original_safe).suffix or '.txt'}"
            out_path = job_dir / "output" / out_name
            out_path.write_text(anon_text_with_header, encoding="utf-8")

        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=g.job_id,
            file_size=g.file_size,
            entities_found=g.entities_found,
            status_code=200,
        )
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_name,
            mimetype="text/plain; charset=utf-8",
        )

    @app.post("/decode")
    def decode_route():
        client_ip = extract_client_ip(request)
        g.client_ip = client_ip
        g.route = request.path
        g.job_id = None
        g.file_size = None
        g.entities_found = None

        if not rate_limiter.allow(client_ip):
            abort(429)

        f = request.files.get("file")
        if not f or not f.filename:
            abort(400, "No file uploaded")
        validation_error = validate_txt_upload(f)
        if validation_error:
            abort(400, validation_error)

        uploaded_name = f.filename
        raw = f.read()
        g.file_size = len(raw)
        if len(raw) > MAX_UPLOAD_BYTES:
            abort(413)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            abort(400, "File must be valid UTF-8 TXT.")

        job_id = extract_job_id_from_text(text) or extract_job_id_from_filename(uploaded_name)
        if not job_id:
            abort(400, "Cannot find job_id. File must include '## ANON_JOB: ...' header or correct filename.")
        g.job_id = job_id

        with connect(db_path) as conn:
            mapping = load_mapping_dict(conn, job_id)

        if not mapping:
            abort(404, f"No mapping found for job_id: {job_id}")

        restored = deanonymize(text, mapping)

        ts2 = now_timestamp_ms()
        job_dir = storage_dir / job_id
        (job_dir / "output").mkdir(parents=True, exist_ok=True)

        safe_uploaded = sanitize_filename(uploaded_name)
        base_stem = Path(safe_uploaded).stem
        out_name = f"{base_stem}__DEANON__{job_id}__{ts2}.txt"
        out_path = job_dir / "output" / out_name
        out_path.write_text(restored, encoding="utf-8")

        log_event(
            app_logger,
            route=request.path,
            client_ip=client_ip,
            job_id=g.job_id,
            file_size=g.file_size,
            entities_found=None,
            status_code=200,
        )
        return send_file(
            out_path,
            as_attachment=True,
            download_name=out_name,
            mimetype="text/plain; charset=utf-8",
        )

    @app.errorhandler(400)
    def error_400(err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=400,
        )
        return render_template("errors/400.html", message=getattr(err, "description", "Invalid request.")), 400

    @app.errorhandler(404)
    def error_404(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=404,
        )
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def error_413(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=413,
        )
        return render_template("errors/413.html", limit_mb=MAX_UPLOAD_BYTES // (1024 * 1024)), 413

    @app.errorhandler(429)
    def error_429(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=429,
        )
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def error_500(_err):
        log_event(
            app_logger,
            route=request.path,
            client_ip=getattr(g, "client_ip", extract_client_ip(request)),
            job_id=getattr(g, "job_id", None),
            file_size=getattr(g, "file_size", request.content_length),
            entities_found=getattr(g, "entities_found", None),
            status_code=500,
        )
        return render_template("errors/500.html"), 500

    return app
