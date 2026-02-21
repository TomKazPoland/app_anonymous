# AGENTS.md
## Project: anonymous_app (Flask, Passenger, subpath deployment)

This file defines mandatory operational rules for Codex / AI agents
working on this repository.

Breaking these rules is considered a regression risk.

---

# 1. PROJECT CONTEXT (CRITICAL)

## Deployment

Production URL:
https://potrzebuje.pl/apps/anonymous/

The application is deployed under a SUBPATH:
`/apps/anonymous`

It is NOT deployed at domain root.

Hosting:
- cPanel
- Passenger (WSGI)
- Python 3.9 virtualenv managed by hosting

Restart mechanism:
touch tmp/restart.txt

Logs:
- stderr.log
- logs/app.log

---

# 2. ARCHITECTURE

Structure:

anonymous_app/
│
├── app/
│   └── main.py (create_app factory)
│
├── templates/
│   └── index.html
│
├── static/
│
├── passenger_wsgi.py
│
├── requirements.txt
│
└── AGENTS.md

Local development:
- Python 3.10
- .venv310

Production:
- Python 3.9 (hosting virtualenv)

---

# 3. NON-NEGOTIABLE RULES

1) NEVER break a working feature.
2) NEVER refactor without explicit request.
3) ALWAYS assume subpath deployment.
4) NEVER introduce absolute URLs like:
   action="/encode"
   href="/something"

   Use:
   action="encode"
   action="./encode"
   or url_for with correct prefix awareness.

5) Before changing routing, inspect:
   - endpoint names
   - allowed methods (GET vs POST)
   - subpath behavior

---

# 4. SURE METHODOLOGY (MANDATORY)

Before ANY modification:

## S — Snapshot
- Backup files being modified (timestamped copy)
- Capture last 50 lines of:
  stderr.log
  logs/app.log

## U — Understand
- Identify problem layer:
  HTML
  Flask routing
  WSGI
  Passenger
  subpath prefix
  browser behavior (GET vs POST)

- Explicitly list:
  What is known
  What is assumed
  What is missing

## R — Run pre-checks
- Verify import:
  from app.main import create_app
- Verify endpoints:
  app.url_map
- Verify template form actions
- Verify no absolute paths for subpath app

## E — Execute
- Apply minimal patch
- Restart passenger
- Smoke test:
  GET /apps/anonymous/ -> 200
  POST /apps/anonymous/encode -> expected behavior
- Re-check logs

If any regression appears:
Rollback immediately.

---

# 5. SUBPATH DEPLOYMENT RULES

Because the app runs under:

/apps/anonymous

All links and forms must be:

RELATIVE PATHS

Correct:
action="encode"

Incorrect:
action="/encode"

Reason:
Absolute paths break subpath deployment.

---

# 6. CHANGE POLICY

Allowed without explicit approval:
- Bug fix
- Path correction
- Logging improvement

NOT allowed without explicit approval:
- Refactor
- Dependency upgrade
- Flask major version change
- Routing redesign

---

# 7. OUTPUT FORMAT EXPECTED FROM AGENT

All instructions must:
- Be copy-paste ready
- Include full path guards (cd /full/path || exit 1)
- Show BEFORE / AFTER
- Include restart step
- Include verification step

No partial diffs.
No vague suggestions.

---

# 8. REGRESSION PROTECTION

If something previously worked,
it must remain working after modification.

Regression is unacceptable.

---

# END OF AGENT RULES

