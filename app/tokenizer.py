from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable

from .pii_detector import Entity


@dataclass
class TokenMapping:
    token: str
    entity_type: str
    original_value: str


TOKEN_SECRET_FILE = Path("/home/potrzebuje/Projects/Secrets/anonymous_token_hmac_key.txt")
_WS_RE = re.compile(r"\s+")

def _load_token_secret() -> bytes:
    secret = TOKEN_SECRET_FILE.read_text(encoding="utf-8").strip()
    if not secret:
        raise RuntimeError(f"Empty token secret file: {TOKEN_SECRET_FILE}")
    return secret.encode("utf-8")

def _normalize_for_token(entity_type: str, value: str) -> str:
    s = value.strip()

    if entity_type in {"PESEL", "REGON", "KRS", "PAN", "IMEI", "PHONE"}:
        return re.sub(r"\D", "", s)

    if entity_type == "NIP":
        compact = re.sub(r"[^A-Za-z0-9]", "", s).upper()
        if compact.startswith("PL") and len(compact) == 12 and compact[2:].isdigit():
            return compact
        return re.sub(r"\D", "", s)

    if entity_type in {"IBAN", "BIC", "MAC", "VIN", "PLATE", "DOCUMENT"}:
        return re.sub(r"[^A-Za-z0-9]", "", s).upper()

    if entity_type == "EMAIL":
        return _WS_RE.sub("", s).lower()

    if entity_type in {"PERSON", "ADDRESS"}:
        return _WS_RE.sub(" ", s).strip().lower()

    if entity_type in {"IP", "GPS"}:
        return _WS_RE.sub("", s)

    return _WS_RE.sub(" ", s).strip()

def _token_id(entity_type: str, value: str, length: int = 12) -> str:
    normalized = _normalize_for_token(entity_type, value)
    payload = f"{entity_type}|{normalized}".encode("utf-8")
    digest = hmac.new(_load_token_secret(), payload, hashlib.sha256).hexdigest().upper()
    return digest[:length]


def _build_occurrence_tokens(entities: Iterable[Entity], text: str) -> list[tuple[Entity, str, str]]:
    ordered = list(entities)
    ordered.sort(key=lambda e: e.start)

    counters: dict[tuple[str, str], int] = {}
    prepared: list[tuple[Entity, str, str]] = []

    for e in ordered:
        original_fragment = text[e.start:e.end]
        stable_id = _token_id(e.type, original_fragment)
        key = (e.type, stable_id)
        counters[key] = counters.get(key, 0) + 1
        occ_id = f"{counters[key]:04d}"
        prepared.append((e, original_fragment, "{PZ:%s:%s:%s}" % (e.type, stable_id, occ_id)))

    return prepared


def anonymize(text: str, entities: Iterable[Entity]) -> tuple[str, list[TokenMapping]]:
    mappings: list[TokenMapping] = []
    out = text

    prepared = _build_occurrence_tokens(entities, text)

    for e, original_fragment, token in sorted(prepared, key=lambda item: item[0].start, reverse=True):
        mappings.append(TokenMapping(token=token, entity_type=e.type, original_value=original_fragment))
        out = out[:e.start] + token + out[e.end:]

    mappings.reverse()
    return out, mappings


# === TOKEN_HMAC_PATCH_V3 ===


# === TOKEN_V3_STABLEID_OCCID_PATCH_V1 ===
