from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Iterable

from .pii_detector import Entity


@dataclass
class TokenMapping:
    token: str
    entity_type: str
    original_value: str


def _rand(nbytes: int = 6) -> str:
    # urlsafe base64-ish without punctuation surprises
    return secrets.token_urlsafe(nbytes).replace("-", "").replace("_", "")[:12]


def anonymize(text: str, entities: Iterable[Entity]) -> tuple[str, list[TokenMapping]]:
    mappings: list[TokenMapping] = []
    out = text

    # Replace from the end to keep offsets valid
    ents = list(entities)
    ents.sort(key=lambda e: e.start, reverse=True)

    for e in ents:
        token = "{PZ:%s:%s}" % (e.type, _rand())
        mappings.append(TokenMapping(token=token, entity_type=e.type, original_value=e.value))
        out = out[:e.start] + token + out[e.end:]

    mappings.reverse()
    return out, mappings
