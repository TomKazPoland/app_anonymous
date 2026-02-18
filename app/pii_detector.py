from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    type: str
    value: str


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PESEL_RE = re.compile(r"\b\d{11}\b")

# +48 600 700 800, +48600700800, +1-202-555-0101 etc.
PHONE_INTL_RE = re.compile(r"\+\d{1,3}(?:[ \-]?\d){6,14}\b")

# Polish 9-digit patterns: 600700800 / 600 700 800 / 600-700-800
PHONE_PL9_RE = re.compile(r"\b\d{3}(?:[ \-]?\d{3}){2}\b")


def detect(text: str) -> list[Entity]:
    entities: list[Entity] = []

    # EMAIL first
    for m in EMAIL_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "EMAIL", m.group(0)))

    # PESEL next
    for m in PESEL_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "PESEL", m.group(0)))

    # Phones
    for m in PHONE_INTL_RE.finditer(text):
        val = m.group(0).strip()
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 9:
            entities.append(Entity(m.start(), m.end(), "PHONE", val))

    for m in PHONE_PL9_RE.finditer(text):
        val = m.group(0).strip()
        digits = re.sub(r"\D", "", val)
        # only 9-digit, avoid PESEL and other patterns
        if len(digits) == 9:
            entities.append(Entity(m.start(), m.end(), "PHONE", val))

    # Sort and remove overlaps (prefer earlier added: EMAIL/PESEL before PHONE)
    entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
    cleaned: list[Entity] = []
    last_end = -1
    for e in entities:
        if e.start >= last_end:
            cleaned.append(e)
            last_end = e.end

    return cleaned
