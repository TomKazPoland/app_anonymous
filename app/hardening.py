from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIMETYPES = {"text/plain", "application/octet-stream"}
RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 5 * 60


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._by_ip: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        key = client_ip or "unknown"
        with self._lock:
            entries = [ts for ts in self._by_ip.get(key, []) if ts >= cutoff]
            if len(entries) >= self.max_requests:
                self._by_ip[key] = entries
                return False
            entries.append(now)
            self._by_ip[key] = entries
            return True


def extract_client_ip(req) -> str:
    xff = req.headers.get("X-Forwarded-For", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return (req.remote_addr or "unknown").strip() or "unknown"


def validate_txt_upload(file_storage) -> Optional[str]:
    filename = (file_storage.filename or "").strip()
    if not filename:
        return "No file uploaded."
    if not filename.lower().endswith(".txt"):
        return "Only .txt files are supported."
    if file_storage.mimetype not in ALLOWED_MIMETYPES:
        return "Invalid file type. Upload UTF-8 TXT only."
    return None


def setup_app_logger(logs_dir: Path) -> logging.Logger:
    logger = logging.getLogger("anonymous_app")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(logs_dir / "app.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def log_event(
    logger: logging.Logger,
    *,
    route: str,
    client_ip: str,
    status_code: int,
    job_id: Optional[str] = None,
    file_size: Optional[int] = None,
    entities_found: Optional[int] = None,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "route": route,
        "client_ip": client_ip,
        "job_id": job_id,
        "file_size": file_size,
        "entities_found": entities_found,
        "status_code": status_code,
    }
    logger.info(json.dumps(payload, ensure_ascii=True))
