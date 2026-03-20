from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Entity:
    start: int
    end: int
    type: str
    value: str


EMAIL_RE = re.compile(
    r'(?<![A-Za-z0-9_])(?:"[^"\r\n]+"|[A-Za-z0-9._%+\-]+)\s*@\s*[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?![A-Za-z0-9_])'
)
PESEL_RE = re.compile(r"\b\d{11}\b")

PHONE_INTL_RE = re.compile(r"\+\d{1,3}(?:[^\w\r\n]*\d){6,14}\b")
PHONE_PL9_RE = re.compile(r"\b\d{3}(?:[^\w\r\n]*\d{3}){2}\b")

PAN_RE = re.compile(r"(?<!\d)\d(?:[^\w\r\n]?\d){12,18}(?!\d)")
IMEI_RE = re.compile(r"(?<!\d)\d(?:[^\w\r\n]?\d){14}(?!\d)")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ \-]?[A-Z0-9]){11,30}\b", re.IGNORECASE)

IP_RE = re.compile(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)")
MAC_RE = re.compile(r"(?<![A-Fa-f0-9])(?:[A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}(?![A-Fa-f0-9])")
GPS_RE = re.compile(r"(?<!\d)([-+]?(?:[1-8]?\d(?:\.\d+)?|90(?:\.0+)?))\s*,\s*([-+]?(?:1[0-7]\d(?:\.\d+)?|[1-9]?\d(?:\.\d+)?|180(?:\.0+)?))(?!\d)")
VIN_RE = re.compile(r"(?<![A-Z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Z0-9])")

PERSON_SURNAME_COMMA_RE = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+,\s*[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\b")
PERSON_NAME_SURNAME_RE = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\b")
PERSON_QUOTED_RE = re.compile(r'"[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+"')
PERSON_SEMICOLON_RE = re.compile(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+;[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\b")

ADDRESS_FULL_RE = re.compile(
    r"\b(?:ul\.|al\.|pl\.|os\.)\s+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż0-9 .-]+\s+\d+[A-Za-z]?(?:\s*m\.\s*\d+)?,\s*\d{2}-\d{3}\s+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż -]+\b"
)




ID_CARD_META_RE = re.compile(r'(?i)\b(?:id_card|dowod|dowód)\b\s*[:=]\s*[\'"\"]?([A-Z]{3}\d{6})[\'"\"]?')
PASSPORT_META_RE = re.compile(r'(?i)\b(?:passport|paszport)\b\s*[:=]\s*[\'"\"]?([A-Z]{2}\d{7})[\'"\"]?')

LABEL_IMEI = re.compile(r"\bIMEI\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_PAN = re.compile(r"\bPAN\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_PESEL = re.compile(r"\bPESEL\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_NIP = re.compile(r"\bNIP\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_REGON = re.compile(r"\bREGON\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_KRS = re.compile(r"\bKRS\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_IBAN = re.compile(r"\bIBAN\b(?:\s*[:=\-]>\s*|\s+)*", re.IGNORECASE)
LABEL_DOCUMENT = re.compile(
    r"\b(?:NR[ _-]?DOKUMENTU|NUMER[ _-]?DOKUMENTU|DOKUMENT|DOW[ÓO]D|PASZPORT|ID)\b(?:\s*[:=\-]>\s*|\s+)*",
    re.IGNORECASE,
)
LABEL_PLATE = re.compile(
    r"\b(?:NR[ _-]?REJ(?:ESTRACYJNY)?|NUMER[ _-]?REJ(?:ESTRACYJNY)?|TABLICA|TABLICE|REJESTRACJA)\b(?:\s*[:=\-]>\s*|\s+)*",
    re.IGNORECASE,
)


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def _alnum_only_upper(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _luhn_ok(number: str) -> bool:
    if not number.isdigit():
        return False
    total = 0
    rev = number[::-1]
    for i, ch in enumerate(rev):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _iban_ok(value: str) -> bool:
    iban = _alnum_only_upper(value)
    if len(iban) < 15 or len(iban) > 34:
        return False
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", iban):
        return False

    moved = iban[4:] + iban[:4]
    converted_parts = []
    for ch in moved:
        if ch.isdigit():
            converted_parts.append(ch)
        else:
            converted_parts.append(str(ord(ch) - 55))
    converted = "".join(converted_parts)

    mod = 0
    for ch in converted:
        mod = (mod * 10 + int(ch)) % 97
    return mod == 1


def _extract_labeled_digits(text: str, label_re, min_len: int, max_len: int):
    results = []
    for m in label_re.finditer(text):
        i = m.end()
        digits = ""
        value_start = None
        value_end = None
        while i < len(text) and len(digits) < max_len:
            ch = text[i]
            if ch.isdigit():
                if value_start is None:
                    value_start = i
                digits += ch
                value_end = i + 1
            elif ch in " -:./|_\n\t=>":
                pass
            else:
                break
            i += 1

        if min_len <= len(digits) <= max_len and value_start is not None and value_end is not None:
            results.append((value_start, value_end, digits))
    return results


def _extract_labeled_iban(text: str):
    results = []
    for m in LABEL_IBAN.finditer(text):
        i = m.end()
        chars = ""
        value_start = None
        value_end = None
        while i < len(text) and len(_alnum_only_upper(chars)) < 34:
            ch = text[i]
            if ch.isalnum():
                if value_start is None:
                    value_start = i
                chars += ch
                value_end = i + 1
            elif ch in " -:./|_\n\t=>":
                if value_start is not None:
                    chars += ch
            else:
                break
            i += 1

        normalized = _alnum_only_upper(chars)
        if _iban_ok(normalized) and value_start is not None and value_end is not None:
            results.append((value_start, value_end, normalized))
    return results


def _extract_labeled_token(text: str, label_re, min_len: int, max_len: int):
    results = []
    for m in label_re.finditer(text):
        i = m.end()
        raw = ""
        value_start = None
        value_end = None
        started = False

        while i < len(text):
            ch = text[i]
            if ch.isalnum():
                if value_start is None:
                    value_start = i
                raw += ch
                value_end = i + 1
                started = True
            elif ch in " -/_\n\t":
                if started:
                    raw += ch
            elif ch in ":=>":
                pass
            else:
                break
            i += 1
            if len(_alnum_only_upper(raw)) >= max_len:
                break

        normalized = _alnum_only_upper(raw)
        if min_len <= len(normalized) <= max_len and value_start is not None and value_end is not None:
            results.append((value_start, value_end, normalized))
    return results


def _document_token_ok(value: str) -> bool:
    token = _alnum_only_upper(value)
    if len(token) < 5 or len(token) > 20:
        return False
    if not any(ch.isalpha() for ch in token):
        return False
    if not any(ch.isdigit() for ch in token):
        return False
    return True


def _plate_token_ok(value: str) -> bool:
    token = _alnum_only_upper(value)
    if len(token) < 5 or len(token) > 9:
        return False
    if not re.fullmatch(r"(?:[A-Z]{1,4}[A-Z0-9]{4,5}|[A-Z]{1,3}[A-Z0-9]{4,6})", token):
        return False
    return True



ADDRESS_PREFIX_RE = re.compile(r"\b(?:ul\.|al\.|pl\.|os\.)", re.IGNORECASE)
ADDRESS_POSTCODE_RE = re.compile(r"\b(?:\d{2}-\d{3}|\d{5})\b")
ADDRESS_CITY_AFTER_POSTCODE_RE = re.compile(r"^\s*([A-ZĄĆĘŁŃÓŚŹŻ][A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż -]{1,40})")
ADDRESS_RIGHT_STOP_RE = re.compile(r"(?i)(?:;|\b(?:telefon|tel\.|e-?mail|mail|pesel|nip|iban|bic|swift|vin|tablica|rejestracja|document|dow[oó]d|paszport|imei|mac|ip|gps|krs|regon)\b)")
ADDRESS_LEFT_LABEL_RE = re.compile(r"(?i)(adres[^:]{0,40}:|pod adresem)")

def _extract_address_postcode_anchor_entities(text: str):
    results = []
    lines = text.splitlines(keepends=True)
    offset = 0

    for line in lines:
        line_body = line.rstrip("\n")
        for pm in ADDRESS_POSTCODE_RE.finditer(line_body):
            right = line_body[pm.end():]
            city_m = ADDRESS_CITY_AFTER_POSTCODE_RE.search(right)
            if not city_m:
                continue

            left = line_body[:pm.start()]
            street_hits = list(ADDRESS_PREFIX_RE.finditer(left))
            if not street_hits:
                continue

            start = street_hits[-1].start()

            # jeżeli jest etykieta adresowa bliżej niż początek linii, nie cofamy się dalej niż street prefix
            # adres ma zaczynać się od ul./al./pl./os., nie od całego pola opisowego

            city_end_in_right = city_m.end(1)
            provisional_end = pm.end() + city_end_in_right

            stop_m = ADDRESS_RIGHT_STOP_RE.search(line_body[pm.end():])
            if stop_m:
                stop_abs = pm.end() + stop_m.start()
                provisional_end = min(provisional_end, stop_abs)

            value = line_body[start:provisional_end].rstrip(" .,;:")
            if not value:
                continue

            # minimalny bezpieczny warunek: prefix + postcode + city
            if ADDRESS_PREFIX_RE.search(value) and ADDRESS_POSTCODE_RE.search(value):
                results.append(Entity(offset + start, offset + start + len(value), "ADDRESS", value))

        offset += len(line)

    return results



NIP_ANY_LABEL_RE = re.compile(
    r"(?i)\bNIP\b\s*[:=]?\s*(PL\d{10}|\d{10})\b"
)

BIC_ANY_LABEL_RE = re.compile(
    r"(?i)(?:\bBIC\b|\bSWIFT/BIC\b|\bSWIFT\b)\s*[:=]?\s*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b"
)



def _looks_like_capitalized_name_token(value: str) -> bool:
    return bool(re.fullmatch(r"[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:[- ][A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?", value.strip()))

def _extract_structured_csv_person_entities(text: str):
    results = []
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\n")
        if line.startswith("CSV-like:"):
            payload_start = line.find("CSV-like:") + len("CSV-like:")
            payload = line[payload_start:].lstrip()
            payload_abs_start = payload_start + (len(line[payload_start:]) - len(payload))
            cols = payload.split(";")
            if len(cols) == 10:
                running = payload_abs_start
                col_spans = []
                for idx, col in enumerate(cols):
                    col_start = running
                    col_end = col_start + len(col)
                    col_spans.append((col_start, col_end, col))
                    running = col_end + 1

                # col 1 = surname, col 2 = first name (0-based indexing inside payload => 1 and 2)
                if len(col_spans) >= 3:
                    ln_start, ln_end, ln_val = col_spans[1]
                    fn_start, fn_end, fn_val = col_spans[2]

                    if _looks_like_capitalized_name_token(ln_val):
                        results.append(Entity(offset + ln_start, offset + ln_end, "PERSON_LN", ln_val))
                    if _looks_like_capitalized_name_token(fn_val):
                        results.append(Entity(offset + fn_start, offset + fn_end, "PERSON_FN", fn_val))

        offset += len(raw_line)
    return results



ORG_NABYWCA_RE = re.compile(
    r'(?i)\bNabywca\b\s*:\s*([^\n,]+?(?:\s+(?:sp\.?\s*z\.?\s*o\.?\s*o\.?|sp\.?\s*k\.?|s\.?\s*a\.?|s\.?\s*c\.?))?)'
    r'(?=,\s*(?:NIP|REGON|KRS)\b|$)'
)

def _extract_org_label_entities(text: str):
    results = []
    for m in ORG_NABYWCA_RE.finditer(text):
        value = m.group(1).strip()
        if value:
            results.append(Entity(m.start(1), m.end(1), "ORG", value))
    return results


def detect(text: str) -> list[Entity]:
    entities: list[Entity] = []

    for m in EMAIL_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "EMAIL", m.group(0)))

    for e in _extract_org_label_entities(text):
        entities.append(e)

    for e in _extract_structured_csv_person_entities(text):
        entities.append(e)


    for start, end, digits in _extract_labeled_digits(text, LABEL_PESEL, 11, 11):
        entities.append(Entity(start, end, "PESEL", digits))

    for start, end, digits in _extract_labeled_digits(text, LABEL_NIP, 10, 10):
        entities.append(Entity(start, end, "NIP", digits))

    for start, end, digits in _extract_labeled_digits(text, LABEL_REGON, 9, 14):
        entities.append(Entity(start, end, "REGON", digits))

    for start, end, digits in _extract_labeled_digits(text, LABEL_KRS, 10, 10):
        entities.append(Entity(start, end, "KRS", digits))

    for start, end, digits in _extract_labeled_digits(text, LABEL_IMEI, 15, 15):
        if _luhn_ok(digits):
            entities.append(Entity(start, end, "IMEI", digits))

    for start, end, digits in _extract_labeled_digits(text, LABEL_PAN, 13, 19):
        if _luhn_ok(digits):
            entities.append(Entity(start, end, "PAN", digits))

    for start, end, iban in _extract_labeled_iban(text):
        entities.append(Entity(start, end, "IBAN", iban))

    for start, end, token in _extract_labeled_token(text, LABEL_DOCUMENT, 5, 20):
        if _document_token_ok(token):
            entities.append(Entity(start, end, "DOCUMENT", token))

    for start, end, token in _extract_labeled_token(text, LABEL_PLATE, 5, 9):
        if _plate_token_ok(token):
            entities.append(Entity(start, end, "PLATE", token))

    for m in PESEL_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "PESEL", m.group(0)))

    for m in IBAN_RE.finditer(text):
        raw = m.group(0)
        if _iban_ok(raw):
            entities.append(Entity(m.start(), m.end(), "IBAN", raw))

    for m in IMEI_RE.finditer(text):
        digits = _digits_only(m.group(0))
        if len(digits) == 15:
            entities.append(Entity(m.start(), m.end(), "IMEI", m.group(0)))

    for m in PAN_RE.finditer(text):
        digits = _digits_only(m.group(0))
        if 13 <= len(digits) <= 19 and len(digits) != 15:
            entities.append(Entity(m.start(), m.end(), "PAN", m.group(0)))

    for m in IP_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "IP", m.group(0)))

    for m in MAC_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "MAC", m.group(0)))

    for m in GPS_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "GPS", m.group(0)))

    for m in VIN_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "VIN", m.group(0)))

    for m in PHONE_INTL_RE.finditer(text):
        if len(_digits_only(m.group(0))) >= 9:
            entities.append(Entity(m.start(), m.end(), "PHONE", m.group(0)))

    for m in PHONE_PL9_RE.finditer(text):
        if len(_digits_only(m.group(0))) == 9:
            entities.append(Entity(m.start(), m.end(), "PHONE", m.group(0)))

    for m in PERSON_QUOTED_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "PERSON", m.group(0)))

    for m in PERSON_SURNAME_COMMA_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "PERSON", m.group(0)))

    for m in PERSON_SEMICOLON_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.start())
        if line_end == -1:
            line_end = len(text)
        line_text = text[line_start:line_end]
        if line_text.startswith("CSV-like:"):
            continue
        entities.append(Entity(m.start(), m.end(), "PERSON", m.group(0)))

    for m in PERSON_NAME_SURNAME_RE.finditer(text):
        entities.append(Entity(m.start(), m.end(), "PERSON", m.group(0)))

    for e in _extract_address_postcode_anchor_entities(text):
        entities.append(e)

    for m in ID_CARD_META_RE.finditer(text):
        entities.append(Entity(m.start(1), m.end(1), "DOCUMENT", m.group(1)))

    for m in PASSPORT_META_RE.finditer(text):
        entities.append(Entity(m.start(1), m.end(1), "DOCUMENT", m.group(1)))

    for m in NIP_ANY_LABEL_RE.finditer(text):
        entities.append(Entity(m.start(1), m.end(1), "NIP", m.group(1)))

    for m in BIC_ANY_LABEL_RE.finditer(text):
        entities.append(Entity(m.start(1), m.end(1), "BIC", m.group(1)))

    _type_priority = {"ORG": 4, "PERSON_LN": 3, "PERSON_FN": 3, "PERSON": 2}
    entities.sort(key=lambda e: (e.start, -_type_priority.get(e.type, 1), -(e.end - e.start)))
    cleaned: list[Entity] = []
    last_end = -1
    for e in entities:
        if e.start >= last_end:
            cleaned.append(e)
            last_end = e.end

    return cleaned


# === HOL_MIN_GLOBAL_PATTERN_PATCH_V2 ===


# === HELPER_RANGE_PATCH_V1 ===


# === PAN_IMEI_BROAD_PATCH_V3 ===


# === PERSON_ADDRESS_PATCH_V1 ===


# === DOCUMENT_META_PATCH_V1 ===


# === KRS_LABEL_PATCH_V1 ===


# === ADDRESS_POSTCODE_ANCHOR_PATCH_V1 ===


# === NIP_BIC_PATCH_V2 ===


# === PERSON_STRUCTURED_CSV_PATCH_V1 ===


# === PLATE_FIX_V2 ===


# === PLATE_FIX_V3 ===


# === ORG_V1_NABYWCA_PATCH_V1 ===
