# ANONYMOUS — Agent Rules (Codex)

Purpose: reversible anonymization for UTF-8 TXT (ENCODE) and restoration (DECODE).
Security-first. Minimal, incremental changes only.

## 0) Non-negotiables (must always hold)
- NEVER print/log/store secrets or plaintext PII outside controlled encrypted storage.
- NEVER write secrets, DB, or uploads under public_html.
- NEVER commit secrets, DB, storage, logs. Keep `.gitignore` intact.
- Keep diffs small: implement only requested change; avoid unrelated refactors.

## 1) Repo + runtime topology (CRITICAL)
Local dev (laptop):
- Repo: `~/Projects/anonymous_app`
- Secrets (OUTSIDE repo): `~/secrets/`
  - `openai_key.python.env` (dotenv)
  - `anon_mapping_key.python.env` (dotenv)
- Sensitive runtime (gitignored): `data/`, `storage/`, `logs/`

Production server:
- Public mount (routing only): `/home/potrzebu/public_html/ANONYMOUS`
- App code root (outside webroot): `/home/potrzebu/Projects/anonymous_app`
- Secrets (outside webroot): `/home/potrzebu/secrets/`
- Passenger `.htaccess` points PassengerAppRoot to app code root.

Rule: public mount must contain only minimal routing assets (e.g., .htaccess). No code, no DB, no uploads.

## 2) Secrets policy
Load secrets by priority:
1) environment variables
2) `${SECRETS_DIR:-$HOME/secrets}/<file>.env` via dotenv

Required keys:
- `ANON_MAPPING_KEY` (Fernet) from `anon_mapping_key.python.env`
Optional/ future:
- `OPENAI_API_KEY` from `openai_key.python.env`

Do not echo secrets. Do not write secrets into repo, logs, or templates.

## 3) Core behavior (must not regress)
ENCODE:
- Input: UTF-8 TXT
- Output: TXT with header on FIRST LINE:
  `## ANON_JOB: <job_id>`
- Replace detected PII with tokens (must remain inside curly braces):
  `{PZ:<TYPE>:<TOKEN>}` where TYPE ∈ {EMAIL, PESEL, PHONE, ...}
- Mapping stored per job_id in SQLite: `data/mapping.db`
- Mapping values MUST be encrypted at rest (Fernet) and decrypted only in-memory during DECODE.

DECODE:
- Extract `job_id` from header OR filename fallback.
- Replace only recognized `{PZ:...}` tokens using mapping for that job_id.
- The rest of the text must remain as-is (preserve edits outside tokens).

## 4) job_id + filenames (stability rules)
- job_id format includes: autoincrement job_no + timestamp_ms + original full filename (for correlation).
- Do NOT attempt to anonymize original filename in v1.
- For filesystem writes, sanitize filename safely, but keep original_full in job_id metadata.
- Output filenames are controlled by app (user must NOT rename output).

## 5) Storage rules
- Write per-job artifacts under: `storage/<job_id>/{input,output}/`
- All storage is sensitive and gitignored.
- Future: retention/cleanup may be implemented (e.g., delete > 1 day) but must be opt-in and safe.

## 6) Logging rules (PII-safe)
Allowed logs: job_id, counts, sizes, durations, errors without payload.
Forbidden logs: uploaded text, detected PII, decrypted values, raw mappings.
If adding debug: guard behind a flag and keep it payload-free.

## 7) Scope limits
v1 scope: TXT only (UTF-8).
Future scope (later): DOCX/Word, PDF etc. Not now.

## 8) Dev commands (local)
- venv: `python3 -m venv .venv && source .venv/bin/activate`
- deps: `pip install -r requirements.txt`
- run: `./run_local.sh` (127.0.0.1:8001)

## 9) How to work (agent procedure)
When implementing changes:
1) Write a 1–3 bullet plan.
2) Change minimal set of files.
3) Provide verification steps (commands + expected results).
4) Stop. Do not “continue improving” unless asked.

