import re

IBAN_RE = re.compile(r"\bPL(?:\s*\d){26}\b", re.IGNORECASE)
BIC_RE = re.compile(r"\b[A-Z]{4}PL[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b")
PAN_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
IMEI_RE = re.compile(r"\b\d{15}\b")
GPS_RE = re.compile(r"\b-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b")

def _digits_only(value):
    return "".join(ch for ch in value if ch.isdigit())

def _compact(value):
    return re.sub(r"[\s\-]+", "", value.strip())

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
    return (total % 10) == 0

def _iban_ok(value):
    iban = re.sub(r"\s+", "", value).upper()
    if not iban.startswith("PL") or len(iban) != 28:
        return False
    rearranged = iban[4:] + iban[:4]
    converted = ""
    for ch in rearranged:
        if ch.isdigit():
            converted += ch
        elif "A" <= ch <= "Z":
            converted += str(ord(ch) - 55)
        else:
            return False
    remainder = 0
    for ch in converted:
        remainder = (remainder * 10 + int(ch)) % 97
    return remainder == 1

def _ipv4_ok(ip):
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit():
            return False
        n = int(p)
        if n < 0 or n > 255:
            return False
    return True

def _gps_ok(value):
    try:
        a, b = [x.strip() for x in value.split(",")]
        lat = float(a)
        lon = float(b)
        return (-90.0 <= lat <= 90.0) and (-180.0 <= lon <= 180.0)
    except Exception:
        return False

def _scan_context_values(text, labels, value_rx):
    label_alt = "(?:" + "|".join(labels) + ")"
    same = re.compile(
        rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?({value_rx})"
    )
    nextline = re.compile(
        rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?\n\s*({value_rx})"
    )
    out = []
    for rx in (same, nextline):
        for m in rx.finditer(text):
            out.append((m.start(1), m.end(1), m.group(1)))
    return out

def detect_financial_technical(text):
    entities = []

    # unlabeled or labeled IBAN
    for m in IBAN_RE.finditer(text):
        raw = m.group(0)
        if _iban_ok(raw):
            entities.append((m.start(), m.end(), "IBAN", re.sub(r"\s+", "", raw).upper()))
    for start, end, raw in _scan_context_values(text, [r"IBAN", r"rachunek", r"konto"], r"(?:PL[\d\s]{26,40})"):
        if _iban_ok(raw):
            entities.append((start, end, "IBAN", re.sub(r"\s+", "", raw).upper()))

    # BIC
    for m in BIC_RE.finditer(text):
        entities.append((m.start(), m.end(), "BIC", m.group(0)))
    for start, end, raw in _scan_context_values(text, [r"BIC", r"SWIFT(?:/BIC)?"], r"(?:[A-Z]{4}PL[A-Z0-9]{2}(?:[A-Z0-9]{3})?)"):
        entities.append((start, end, "BIC", raw.strip().upper()))

    # IMEI before PAN
    for m in IMEI_RE.finditer(text):
        raw = m.group(0)
        if _luhn_ok(raw):
            entities.append((m.start(), m.end(), "IMEI", raw))
    for start, end, raw in _scan_context_values(text, [r"IMEI"], r"(?:\d[\d\s\-]{13,18}\d)"):
        normalized = _compact(raw)
        if len(normalized) == 15 and _luhn_ok(normalized):
            entities.append((start, end, "IMEI", normalized))

    # PAN
    for m in PAN_RE.finditer(text):
        raw = m.group(0)
        digits = _digits_only(raw)
        if 13 <= len(digits) <= 19 and _luhn_ok(digits) and len(digits) != 15:
            entities.append((m.start(), m.end(), "PAN", raw))
    for start, end, raw in _scan_context_values(text, [r"karta", r"card"], r"(?:\d[\d\s\-]{11,22}\d)"):
        digits = _digits_only(raw)
        if 13 <= len(digits) <= 19 and _luhn_ok(digits) and len(digits) != 15:
            entities.append((start, end, "PAN", raw))

    # IP
    for m in IP_RE.finditer(text):
        raw = m.group(0)
        if _ipv4_ok(raw):
            entities.append((m.start(), m.end(), "IP", raw))
    for start, end, raw in _scan_context_values(text, [r"IP", r"client_ip"], r"(?:\d{1,3}(?:\.\d{1,3}){3})"):
        if _ipv4_ok(raw):
            entities.append((start, end, "IP", raw))

    # MAC
    for m in MAC_RE.finditer(text):
        entities.append((m.start(), m.end(), "MAC", m.group(0)))
    for start, end, raw in _scan_context_values(text, [r"MAC", r"device_mac"], r"(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})"):
        entities.append((start, end, "MAC", raw))

    # VIN
    for start, end, raw in _scan_context_values(text, [r"VIN"], r"(?:[A-HJ-NPR-Z0-9]{17})"):
        entities.append((start, end, "VIN", raw.strip().upper()))

    # GPS
    for m in GPS_RE.finditer(text):
        raw = m.group(0)
        if _gps_ok(raw):
            entities.append((m.start(), m.end(), "GPS", raw))
    for start, end, raw in _scan_context_values(text, [r"GPS", r"gps"], r"(?:-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,})"):
        if _gps_ok(raw):
            entities.append((start, end, "GPS", raw))

    return entities
