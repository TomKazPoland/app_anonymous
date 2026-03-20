from __future__ import annotations

import re
from typing import Optional


HEADER_RE = re.compile(r"^##\s*ANON_JOB:\s*(.+)\s*$")
TOKEN_RE = re.compile(r"\{PZ:[A-Z_]+:[A-Za-z0-9]+(?::[A-Za-z0-9]+)?\}")


def extract_job_id_from_text(text: str) -> Optional[str]:
    first_line = text.splitlines()[0] if text else ""
    m = HEADER_RE.match(first_line)
    if m:
        return m.group(1).strip()
    return None


def extract_job_id_from_filename(filename: str) -> Optional[str]:
    m = re.search(r"(JOB-\d+-\d{8}-\d{6}-\d{3}--.+)", filename)
    if m:
        return m.group(1)
    return None


def _normalize_mapping_for_decode(mapping) -> dict[str, str]:
    if isinstance(mapping, dict):
        return mapping

    normalized: dict[str, str] = {}
    if isinstance(mapping, list):
        for item in mapping:
            token = getattr(item, "token", None)
            original_value = getattr(item, "original_value", None)
            if isinstance(token, str) and isinstance(original_value, str):
                normalized[token] = original_value
    return normalized


def deanonymize(text: str, mapping) -> str:
    normalized_mapping = _normalize_mapping_for_decode(mapping)

    def repl(m: re.Match) -> str:
        tok = m.group(0)
        return normalized_mapping.get(tok, tok)

    return TOKEN_RE.sub(repl, text)


# === TOKEN_V3_DECODER_PATCH_V1 ===
