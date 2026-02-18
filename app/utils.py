from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def now_timestamp_ms() -> str:
    # YYYYMMDD-HHMMSS-mmm
    dt = datetime.now()
    return dt.strftime("%Y%m%d-%H%M%S-") + f"{int(dt.microsecond/1000):03d}"


def sanitize_filename(name: str) -> str:
    # Keep your "full filename" concept, but make it safe for filesystem.
    # Replace path separators and unsafe chars with underscore.
    name = name.strip()
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[:*?"<>|]', "_", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    return name


def project_root() -> Path:
    # .../anonymous_app/app/utils.py -> project root is parent of "app"
    return Path(__file__).resolve().parents[1]
