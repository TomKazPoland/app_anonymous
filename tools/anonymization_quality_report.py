#!/usr/bin/env python3
import re
import sys
from pathlib import Path

def count(pattern, text, flags=0):
    return len(re.findall(pattern, text, flags))

def pct(masked, total):
    return 0.0 if total == 0 else round(masked * 100.0 / total, 2)

base = Path(__file__).resolve().parent.parent / "benchmarks" / "anonymization"
input_dir = base / "input"
output_dir = base / "output"
report_dir = base / "reports"
report_dir.mkdir(parents=True, exist_ok=True)

inputs = sorted(input_dir.glob("*.txt"))
outputs = sorted(output_dir.glob("*.txt"))

if not inputs:
    print("ERROR: no input benchmark txt file found", file=sys.stderr)
    sys.exit(1)
if not outputs:
    print("ERROR: no output benchmark txt file found", file=sys.stderr)
    sys.exit(1)

inp = inputs[0].read_text(encoding="utf-8", errors="ignore")
out = outputs[0].read_text(encoding="utf-8", errors="ignore")

patterns = {
    "PESEL": r"\b\d{11}\b",
    "PHONE": r"(?:\+48[- ]?\d{3}[- ]?\d{3}[- ]?\d{3}|\b\d{3}[- ]\d{3}[- ]\d{3}\b|\b\d{9}\b)",
    "EMAIL_STD": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "EMAIL_QUOTED": r'"[^"]+"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
    "IBAN": r"\bPL\d{26}\b",
    "CARD_16": r"\b\d{16}\b",
    "CARD_SPACED": r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b",
    "IP": r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
    "MAC": r"\b[0-9A-F]{2}(?::[0-9A-F]{2}){5}\b",
    "IMEI": r"\b\d{15}\b",
    "VIN": r"\b[A-HJ-NPR-Z0-9]{17}\b",
    "GPS": r"\b\d{2}\.\d{6},\s\d{2}\.\d{6}\b",
    "NIP_10": r"\b\d{10}\b",
    "KRS": r"\b\d{10}\b",
    "BIC": r"\b[A-Z]{4}PL[A-Z0-9]{2}[A-Z0-9]{3}\b",
}

lines = []
lines.append("ANONYMIZATION QUALITY REPORT")
lines.append("============================")
lines.append(f"Input file : {inputs[0].name}")
lines.append(f"Output file: {outputs[0].name}")
lines.append("")

header = f"{'Category':<15} {'Input':>8} {'Output':>8} {'Masked':>8} {'Effectiveness%':>14}"
lines.append(header)
lines.append("-" * len(header))

for name, pattern in patterns.items():
    c_in = count(pattern, inp)
    c_out = count(pattern, out)
    masked = max(c_in - c_out, 0)
    lines.append(f"{name:<15} {c_in:>8} {c_out:>8} {masked:>8} {pct(masked, c_in):>14}")

lines.append("")
lines.append("Note: This is a regex-based benchmark helper, not a full semantic evaluator.")

report_path = report_dir / "anonymization_quality_report.txt"
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(report_path)
