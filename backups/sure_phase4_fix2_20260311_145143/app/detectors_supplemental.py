import re

QUOTED_EMAIL_RE = re.compile(
    r'(?i)"[^"\r\n]{1,64}"@(?:[A-Z0-9\-]+\.)+[A-Z]{2,63}'
)

GENERIC_DOC_RE = re.compile(
    r'(?i)\bdokument\s+([A-Z]{3}\d{6})\b'
)

PLATE_RE = re.compile(
    r'(?i)\btablica\s*[:=]\s*([A-Z]{1,3}[ -][A-Z0-9]{3,6})\b'
)

IMEI_RE = re.compile(
    r'(?i)\bimei\s*[:=]\s*([0-9]{15})\b'
)

PAN_LABEL_RE = re.compile(
    r'(?i)\b(?:karta|card)\s*[:=]?\s*([0-9][0-9 \-]{11,25}[0-9])\b'
)

PERSON_PATTERNS = [
    re.compile(
        r'(?im)\bosoba\s+kontaktowa\s*:\s*([A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+(?:\s*,\s*|\s+)[A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+)(?=\s*(?:\||$|\n))'
    ),
    re.compile(
        r'(?im)\bklient\s*:\s*([A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+(?:\s+[A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+){1,2})(?=\s*\()'
    ),
    re.compile(
        r'(?im)\bużytkownik\s+([A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+(?:\s+[A-ZŻŹĆĄŚĘŁÓŃ][A-Za-zŻŹĆĄŚĘŁÓŃąćęłńóśźż\-]+){1,2})(?=\s*\()'
    ),
    re.compile(
        r'(?i)"user"\s*:\s*"([^"\r\n]{3,80})"'
    ),
]


def _digits_only(value):
    return "".join(ch for ch in value if ch.isdigit())


def _luhn_ok(value):
    digits = _digits_only(value)
    if not digits:
        return False
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_supplemental(text):
    entities = []

    for m in QUOTED_EMAIL_RE.finditer(text):
        entities.append((m.start(), m.end(), "EMAIL", m.group(0)))

    for m in GENERIC_DOC_RE.finditer(text):
        entities.append((m.start(1), m.end(1), "DOC_GENERIC", m.group(1).upper()))

    for m in PLATE_RE.finditer(text):
        entities.append((m.start(1), m.end(1), "PLATE", m.group(1).upper()))

    for m in IMEI_RE.finditer(text):
        value = m.group(1)
        if len(value) == 15:
            entities.append((m.start(1), m.end(1), "IMEI", value))

    for m in PAN_LABEL_RE.finditer(text):
        raw = m.group(1).strip()
        digits = _digits_only(raw)
        if 13 <= len(digits) <= 19 and len(digits) != 15 and _luhn_ok(raw):
            entities.append((m.start(1), m.end(1), "PAN", raw))

    for rx in PERSON_PATTERNS:
        for m in rx.finditer(text):
            value = m.group(1).strip()
            if len(value) >= 5:
                entities.append((m.start(1), m.end(1), "PERSON", value))

    return entities
