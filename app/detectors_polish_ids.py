import re

def _digits_only(value):
    return "".join(ch for ch in value if ch.isdigit())

def _compact(value):
    return re.sub(r"[\s\-]+", "", value.strip())

def _strip_pl_prefix(value):
    v = _compact(value).upper()
    if v.startswith("PL"):
        v = v[2:]
    return v

def _nip_ok(value):
    digits = _digits_only(value)
    if len(digits) != 10:
        return False
    weights = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    total = sum(int(digits[i]) * weights[i] for i in range(9))
    return (total % 11) == int(digits[9])

def _regon9_ok(value):
    digits = _digits_only(value)
    if len(digits) != 9:
        return False
    weights = [8, 9, 2, 3, 4, 5, 6, 7]
    total = sum(int(digits[i]) * weights[i] for i in range(8))
    chk = total % 11
    if chk == 10:
        chk = 0
    return chk == int(digits[8])

def _regon14_ok(value):
    digits = _digits_only(value)
    if len(digits) != 14:
        return False
    if not _regon9_ok(digits[:9]):
        return False
    weights = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
    total = sum(int(digits[i]) * weights[i] for i in range(13))
    chk = total % 11
    if chk == 10:
        chk = 0
    return chk == int(digits[13])

def _scan_context_values(text, labels, value_rx):
    # same line: LABEL [spaces] [:=# optional] [spaces] VALUE
    # next line: LABEL [spaces] [:=# optional] newline [spaces] VALUE
    label_alt = "(?:" + "|".join(labels) + ")"
    same = re.compile(
        rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?(?:PL\s*)?({value_rx})"
    )
    nextline = re.compile(
        rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?\n\s*(?:PL\s*)?({value_rx})"
    )
    out = []
    for rx in (same, nextline):
        for m in rx.finditer(text):
            out.append((m.start(1), m.end(1), m.group(1)))
    return out

def detect_polish_ids(text):
    entities = []

    # NIP / VAT-PL
    for start, end, raw in _scan_context_values(
        text,
        [r"NIP", r"VAT[\-_ ]?UE", r"VAT[\-_ ]?PL", r"VAT"],
        r"(?:\d[\d\s\-]{8,14}\d)"
    ):
        normalized = _strip_pl_prefix(raw)
        if _nip_ok(normalized):
            # classify by explicit VAT context if present nearby
            prefix = text[max(0, start - 20):start].upper()
            entity_type = "VAT_PL" if "VAT" in prefix else "NIP"
            entities.append((start, end, entity_type, normalized if entity_type == "NIP" else "PL" + normalized))

    # REGON
    for start, end, raw in _scan_context_values(
        text,
        [r"REGON"],
        r"(?:\d[\d\s\-]{7,18}\d)"
    ):
        normalized = _compact(raw)
        if (len(normalized) == 9 and _regon9_ok(normalized)) or (len(normalized) == 14 and _regon14_ok(normalized)):
            entities.append((start, end, "REGON", normalized))

    # KRS
    for start, end, raw in _scan_context_values(
        text,
        [r"KRS"],
        r"(?:\d[\d\s\-]{8,14}\d)"
    ):
        normalized = _compact(raw)
        if len(normalized) == 10:
            entities.append((start, end, "KRS", normalized))

    # PESEL context-aware (in addition to generic detector)
    for start, end, raw in _scan_context_values(
        text,
        [r"PESEL"],
        r"(?:\d[\d\s\-]{9,14}\d)"
    ):
        normalized = _compact(raw)
        if len(normalized) == 11:
            entities.append((start, end, "PESEL", normalized))

    # ID card
    for start, end, raw in _scan_context_values(
        text,
        [r"dow[oó]d(?:\s+osobisty)?", r"nr\s+dowodu", r"id[_ ]?card"],
        r"(?:[A-Z]{3}\d{6})"
    ):
        entities.append((start, end, "IDCARD", raw.strip().upper()))

    # Passport
    for start, end, raw in _scan_context_values(
        text,
        [r"paszport", r"passport"],
        r"(?:[A-Z]{2}[A-Z0-9]{7})"
    ):
        entities.append((start, end, "PASSPORT", raw.strip().upper()))

    return entities
