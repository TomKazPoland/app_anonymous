# Incident: decode HTTP 500 caused by filename length

Date: 2026-03-31

## Summary
Decode returned HTTP 500 for self-generated files with long names.

## Root cause
The failure was not in mapping or deanonymization logic.
The real failure happened during output write:
- `out_path.write_text(...)`
- exception: `OSError: [Errno 36] File name too long`

## Why it happened
Output filenames contained too much technical data:
- long user stem
- `job_id`
- repeated technical suffixes in decode flow

This exceeded filesystem filename limits.

## Fix implemented
Filename policy was changed.

### Encode output
`<first20_or_less>__CODE__<YYYYMMDD>_<HHMMSS>.<ext>`

### Decode output
Take only the user part before the first `__`, then:
`<first20_or_less>__DECODE__<YYYYMMDD>_<HHMMSS>.txt`

## Important design rule
`job_id` is no longer stored in output filenames.

`job_id` remains available through:
- file header: `## ANON_JOB: ...`
- SQLite mapping
- storage path: `storage/{job_id}/...`

## Cleanup completed
Temporary decode diagnostic trap was removed from `app/main.py`.

Removed elements:
- `decode_trap_log = ...`
- `def _decode_trap(...)`
- all `_decode_trap(...)` calls
- traceback trap logging

## Verification
- CODE OK
- DECODE OK
- CONTENT OK

## Save point
Commit message:
`Fix decode filename-length HTTP 500 and remove diagnostic trap`

Tag:
`savepoint/decode-filename-policy-fix-20260331`
