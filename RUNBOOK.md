# RUNBOOK — ANONYMOUS

Operational manual for the application.

---

## PATHS

- app root: /home/potrzebuje/Projects/anonymous_app
- tmp: /home/potrzebuje/tmp
- logs: logs/
- archive: archive/

---

## RESTART

touch tmp/restart.txt

---

## LOGS

- logs/app.log
- stderr.log (Passenger)

---

## ERROR HANDLING

Flask handles:
- 400 / 404 / 413 / 429 / 500
ONLY if request reaches app

Apache handles:
- everything outside app scope

---

## KNOWN ISSUES

1. SHELL LIMITATION

Some hosting environments do NOT support:

exec > >(tee logfile)

Error:
No such file or directory /dev/fd/XX

Workaround:
bash script.sh | tee logfile

---

2. ARCHITECTURE SPLIT

App != Domain

Flask error handling works only inside app routing

Apache may override errors outside app

---

## RULES (SURE)

- do not assume — verify
- do not overwrite blindly
- always archive before change
- keep docs in repo (never only in chat)

