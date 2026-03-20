# ANONYMOUS

Reversible anonymization system for TXT files.

---

## QUICK START

Full setup instructions:
→ see: SETUP_FOR_NEW_SERVER.md

---

## WHAT THIS APP DOES

- anonymizes sensitive data in TXT
- replaces data with reversible tokens
- allows safe sharing of documents
- supports multi-language UI (pl, en, de, fr, es)

---

## ARCHITECTURE

Application works as:

- Flask app (internal logic)
- deployed under subpath: /apps/anonymous
- hosted via Apache + Passenger (cPanel)

IMPORTANT:

App handles ONLY requests that reach Flask.

Apache / hosting layer handles:
- invalid domain paths
- routing outside app
- some 404/500 cases

This means error pages may differ depending on layer.

---

## LINKS

- Setup: SETUP_FOR_NEW_SERVER.md
- Runbook: RUNBOOK.md
- Rules: AGENTS.md

