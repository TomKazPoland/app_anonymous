#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

def normalize_text(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")

def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())

def compact(value: str) -> str:
    return re.sub(r"[\s\-]+", "", value.strip())

def strip_pl(value: str) -> str:
    v = compact(value).upper()
    if v.startswith("PL"):
        v = v[2:]
    return v

def luhn_ok(value: str) -> bool:
    digits = digits_only(value)
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

def scan_context_values(text, labels, value_rx):
    label_alt = "(?:" + "|".join(labels) + ")"
    same = re.compile(rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?(?:PL\s*)?({value_rx})")
    nextline = re.compile(rf"(?im)\b{label_alt}\b\s*(?:[:=#]\s*)?\n\s*(?:PL\s*)?({value_rx})")
    out = []
    for rx in (same, nextline):
        for m in rx.finditer(text):
            out.append(m.group(1).strip())
    return out

PATTERNS = {
    "PESEL": lambda text: [compact(v) for v in scan_context_values(text, [r"PESEL"], r"(?:\d[\d\s\-]{9,14}\d)")] + [m.group(0) for m in re.finditer(r"\b\d{11}\b", text)],
    "PHONE": lambda text: [m.group(0).strip() for m in re.finditer(r"(?:\+\d{1,3}\(\d{3}\)\d{3}-\d{3}\b)|(?:\+\d{1,3}(?:[ \-]?\d){6,14}\b)|(?:\b\d{3}(?:[ \-]?\d{3}){2}\b)", text)],
    "EMAIL": lambda text: [m.group(0).strip() for m in re.finditer(r'(?i)\b(?:"[^"\r\n]{1,64}"|[A-Z0-9._%+\-]{1,64})@(?:[A-Z0-9\-]+\.)+[A-Z]{2,63}\b', text)],
    "NIP": lambda text: [strip_pl(v) for v in scan_context_values(text, [r"NIP"], r"(?:\d[\d\s\-]{8,14}\d)") if len(strip_pl(v)) == 10],
    "VAT_PL": lambda text: ["PL" + strip_pl(v) for v in scan_context_values(text, [r"VAT[\-_ ]?UE", r"VAT[\-_ ]?PL", r"VAT"], r"(?:\d[\d\s\-]{8,14}\d)") if len(strip_pl(v)) == 10],
    "REGON": lambda text: [compact(v) for v in scan_context_values(text, [r"REGON"], r"(?:\d[\d\s\-]{7,18}\d)")],
    "KRS": lambda text: [compact(v) for v in scan_context_values(text, [r"KRS"], r"(?:\d[\d\s\-]{8,14}\d)")],
    "IDCARD": lambda text: [v.upper() for v in scan_context_values(text, [r"dow[oó]d(?:\s+osobisty)?", r"nr\s+dowodu", r"id[_ ]?card"], r"(?:[A-Z]{3}\d{6})")],
    "PASSPORT": lambda text: [v.upper() for v in scan_context_values(text, [r"paszport", r"passport"], r"(?:[A-Z]{2}[A-Z0-9]{7})")],
    "IBAN": lambda text: [re.sub(r"\s+", "", m.group(0)).upper() for m in re.finditer(r"\bPL(?:\s*\d){26}\b", text, re.IGNORECASE)],
    "BIC": lambda text: [m.group(0).strip().upper() for m in re.finditer(r"\b[A-Z]{4}PL[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b", text)],
    "PAN": lambda text: [m.group(0).strip() for m in re.finditer(r"\b(?:\d[ -]?){13,19}\b", text) if 13 <= len(digits_only(m.group(0))) <= 19 and len(digits_only(m.group(0))) != 15 and luhn_ok(m.group(0))],
    "IMEI": lambda text: [m.group(0).strip() for m in re.finditer(r"\b\d{15}\b", text) if luhn_ok(m.group(0))],
    "IP": lambda text: [m.group(0).strip() for m in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)],
    "MAC": lambda text: [m.group(0).strip() for m in re.finditer(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b", text)],
    "VIN": lambda text: [v.upper() for v in scan_context_values(text, [r"VIN"], r"(?:[A-HJ-NPR-Z0-9]{17})")],
    "GPS": lambda text: [m.group(0).strip() for m in re.finditer(r"\b-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}\b", text)],
    "POSTCODE": lambda text: [m.group(0).strip() for m in re.finditer(r"\b\d{2}-\d{3}\b", text)],
    "PERSON_CTX": lambda text: [m.group(1).strip() for m in re.finditer(r"(?im)^\s*(?:imi[eę]\s+i\s+nazwisko|nazwisko\s+i\s+imi[eę]|osoba\s+kontaktowa|dane\s+klienta|klient|kontrahent)\s*[:#]?\s*([A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+(?:\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-zżźćńółęąś]+){1,2})\s*$", text)],
    "ADDRESS_CTX": lambda text: [m.group(1).strip() for m in re.finditer(r"(?im)^\s*(?:adres(?:\s+(?:zamieszkania|siedziby|korespondencyjny))?)\s*[:#]?\s*(.+?)\s*$", text)],
}

def sample_leaks(values, out_text, limit=8):
    leaks = []
    seen = set()
    for v in values:
        if not v or v in seen:
            continue
        if v in out_text:
            leaks.append(v)
            seen.add(v)
            if len(leaks) >= limit:
                break
    return leaks

def pct(masked, total):
    if total <= 0:
        return None
    return round((masked * 100.0) / total, 1)

def find_record_for_value(lines, value):
    for idx, line in enumerate(lines, start=1):
        if value in line:
            return idx, line.strip()
    return None, None

def explain_issue(kind, value):
    reasons = {
        "NIP": "Wartość NIP pozostała jawna. Najbardziej prawdopodobna przyczyna: wariant pola z separatorem/spacjami/PL lub układ w następnej linii nie został objęty detektorem albo konflikt reguł zatrzymał maskowanie.",
        "VAT_PL": "Wartość VAT_PL pozostała jawna. Najbardziej prawdopodobna przyczyna: niepełny wariant etykiety VAT albo brak zgodności normalizacji z detektorem.",
        "BIC": "Wartość wygląda jak BIC i pozostała jawna. Jeśli to nie jest realny kod bankowy, problemem może być benchmark; jeśli jest realny, trzeba doprecyzować detektor finansowy.",
        "PAN": "Wartość wygląda jak numer karty i pozostała jawna. Możliwa przyczyna: niestandardowy format albo konflikt z rozpoznawaniem IMEI.",
        "IMEI": "To 15-cyfrowy identyfikator urządzenia. Jeśli pozostał jawny, reguła IMEI nie objęła tego wariantu lub koliduje z inną regułą.",
    }
    return reasons.get(kind, "Wartość pozostała jawna w output. Potrzebna korekta detektora lub rozstrzygnięcia konfliktu reguł.")

def main():
    if len(sys.argv) < 3:
        print("USAGE: benchmark_anonymization.py INPUT_FILE OUTPUT_FILE [REPORT_JSON]")
        return 2

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    report_path = Path(sys.argv[3]) if len(sys.argv) >= 4 else None

    if not in_path.is_file():
        print("FATAL: missing input file:", in_path)
        return 3
    if not out_path.is_file():
        print("FATAL: missing output file:", out_path)
        return 4

    in_text = normalize_text(in_path.read_text(encoding="utf-8", errors="replace"))
    out_text = normalize_text(out_path.read_text(encoding="utf-8", errors="replace"))
    lines = in_text.split("\n")

    ordered_types = [
        "PESEL","PHONE","EMAIL",
        "NIP","VAT_PL","REGON","KRS","IDCARD","PASSPORT",
        "PERSON_CTX","ADDRESS_CTX","POSTCODE",
        "IBAN","BIC","PAN","IMEI",
        "IP","MAC","VIN","GPS"
    ]

    summary = {}
    grand_total = 0
    grand_masked = 0

    for key in ordered_types:
        values = PATTERNS[key](in_text)
        total = len(values)
        leaks = sample_leaks(values, out_text)
        remaining = len(leaks)
        masked = max(total - remaining, 0)

        records = []
        for leak in leaks:
            line_no, record = find_record_for_value(lines, leak)
            records.append({
                "value": leak,
                "line_no": line_no,
                "record": record,
                "explanation": explain_issue(key, leak),
            })

        summary[key] = {
            "input_count": total,
            "remaining_in_output": remaining,
            "masked": masked,
            "success_pct": pct(masked, total),
            "sample_leaks": leaks,
            "records_with_issues": records,
        }
        grand_total += total
        grand_masked += masked

    result = {
        "input_file": str(in_path),
        "output_file": str(out_path),
        "global_total": grand_total,
        "global_masked": grand_masked,
        "global_success_pct": pct(grand_masked, grand_total),
        "by_type": summary,
    }

    print("BENCHMARK_RESULT")
    print("INPUT :", in_path)
    print("OUTPUT:", out_path)
    print("GLOBAL_TOTAL       :", grand_total)
    print("GLOBAL_MASKED      :", grand_masked)
    print("GLOBAL_SUCCESS_PCT :", result["global_success_pct"])
    print("")

    for key in ordered_types:
        row = summary[key]
        print(f"{key:12s} in={row['input_count']:4d} remain={row['remaining_in_output']:4d} masked={row['masked']:4d} pct={row['success_pct']}")
        if row["sample_leaks"]:
            for leak in row["sample_leaks"][:3]:
                print("   leak:", leak)

    any_issues = any(summary[k]["records_with_issues"] for k in ordered_types)
    if any_issues:
        print("")
        print("RECORDS_WITH_ISSUES")
        for key in ordered_types:
            records = summary[key]["records_with_issues"]
            if not records:
                continue
            print(f"-- TYPE: {key}")
            for item in records:
                print(f"LINE {item['line_no']}: {item['record']}")
                print(f"WHY : {item['explanation']}")
                print("")

    if report_path:
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("REPORT_JSON:", report_path)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
