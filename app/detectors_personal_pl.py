import re

PERSON_CTX_RE = re.compile(
    r"(?im)^\s*(?:imi[eę]\s+i\s+nazwisko|nazwisko\s+i\s+imi[eę]|osoba\s+kontaktowa|dane\s+klienta|klient|kontrahent)\s*[:#]?\s*([A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+(?:\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+){1,2})\s*$"
)

ADDRESS_CTX_RE = re.compile(
    r"(?im)^\s*(?:adres(?:\s+(?:zamieszkania|siedziby|korespondencyjny))?)\s*[:#]?\s*(.+?)\s*$"
)

STREET_RE = re.compile(
    r"(?i)\b(?:ul\.|al\.|pl\.|os\.)\s*[A-ZŻŹĆĄŚĘŁÓŃ0-9][^,\n]{2,80}"
)

POSTCODE_RE = re.compile(r"\b\d{2}-\d{3}\b")

CITY_RE = re.compile(
    r"\b[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+(?:[\- ][A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+)*\b"
)


def detect_personal_pl(text):
    entities = []

    for m in PERSON_CTX_RE.finditer(text):
        entities.append((m.start(1), m.end(1), "PERSON", m.group(1).strip()))

    for m in ADDRESS_CTX_RE.finditer(text):
        val = m.group(1).strip()
        if len(val) >= 6:
            entities.append((m.start(1), m.end(1), "ADDRESS", val))

    for m in STREET_RE.finditer(text):
        entities.append((m.start(), m.end(), "ADDRESS", m.group(0).strip()))

    for m in POSTCODE_RE.finditer(text):
        entities.append((m.start(), m.end(), "POSTCODE", m.group(0)))

    for m in POSTCODE_RE.finditer(text):
        after = text[m.end():m.end() + 40]
        city_match = re.match(r"\s+([A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+(?:[\- ][A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+)*)", after)
        if city_match:
            city = city_match.group(1)
            start = m.end() + city_match.start(1)
            end = m.end() + city_match.end(1)
            entities.append((start, end, "CITY", city))

    return entities
