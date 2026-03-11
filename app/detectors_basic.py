import re

EMAIL_RE = re.compile(r'(?i)\b(?:"[^"\r\n]{1,64}"|[A-Z0-9._%+\-]{1,64})@(?:[A-Z0-9\-]+\.)+[A-Z]{2,63}\b')
PESEL_RE = re.compile(r"\b\d{11}\b")
PHONE_INTL_RE = re.compile(r"\+\d{1,3}(?:[ \-]?\d){6,14}\b")
PHONE_PAREN_RE = re.compile(r"\+\d{1,3}\(\d{3}\)\d{3}-\d{3}\b")
PHONE_PL9_RE = re.compile(r"\b\d{3}(?:[ \-]?\d{3}){2}\b")


def detect_basic(text):
    entities = []

    for m in EMAIL_RE.finditer(text):
        entities.append((m.start(), m.end(), "EMAIL", m.group(0)))

    for m in PESEL_RE.finditer(text):
        entities.append((m.start(), m.end(), "PESEL", m.group(0)))

    for m in PHONE_INTL_RE.finditer(text):
        val = m.group(0).strip()
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 9:
            entities.append((m.start(), m.end(), "PHONE", val))

    for m in PHONE_PAREN_RE.finditer(text):
        val = m.group(0).strip()
        digits = re.sub(r"\D", "", val)
        if len(digits) >= 9:
            entities.append((m.start(), m.end(), "PHONE", val))

    for m in PHONE_PL9_RE.finditer(text):
        val = m.group(0).strip()
        digits = re.sub(r"\D", "", val)
        if len(digits) == 9:
            entities.append((m.start(), m.end(), "PHONE", val))

    return entities
