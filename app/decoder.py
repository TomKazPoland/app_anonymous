from __future__ import annotations

import re
from typing import Optional


HEADER_RE = re.compile(r"^##\s*ANON_JOB:\s*(.+)\s*$")
TOKEN_RE = re.compile(r"\{PZ:[A-Z_]+:[A-Za-z0-9]+\}")


def extract_job_id_from_text(text: str) -> Optional[str]:
    first_line = text.splitlines()[0] if text else ""
    m = HEADER_RE.match(first_line)
    if m:
        return m.group(1).strip()
    return None


def extract_job_id_from_filename(filename: str) -> Optional[str]:
    # expects ...__ANON__JOB-....txt
    m = re.search(r"(JOB-\d+-\d{8}-\d{6}-\d{3}--.+)", filename)
    if m:
        return m.group(1)
    return None


def deanonymize(text: str, mapping: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        tok = m.group(0)
        return mapping.get(tok, tok)

    # Replace only valid token pattern
    return TOKEN_RE.sub(repl, text)
