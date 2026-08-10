---
name: testing-sams
description: How to run and end-to-end test the Student Academic Management (SAMS) FastAPI + React app locally, including demo logins, seeded data facts, and DB verification queries.
---

# Testing the Student Academic Management app

## Run it (single origin, simplest)

```bash
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then browse `http://localhost:8000` — the FastAPI app serves the built SPA from
`STATIC_DIR` (set in `backend/.env` to `frontend/dist`), so there is no CORS to fight.

If you change frontend code you must rebuild before the browser sees it:

```bash
cd frontend && npm install && npm run build
```

`frontend/.env.production` sets `VITE_API_BASE_URL` empty (same-origin). The Vite dev
server (`npm run dev`, port 5173) instead defaults to `http://localhost:8000` for the API.
Note: on Node 20.18.x Vite prints an engine warning (wants Node 20.19+/22.12+) but the
build still succeeds — don't treat the warning as a failure.

Backend tooling lives in the venv: `backend/.venv/bin/{uvicorn,pytest,ruff}`.

## Demo logins

All demo passwords are `Password123!`. The login page also has one-click role buttons
(Administrator / Teacher / Student / Parent), which is the fastest way to switch roles
in a recording.

| Email | Role | Notes |
| --- | --- | --- |
| admin@school.edu | admin | nav: Overview / Record data / People & classes |
| teacher@school.edu | teacher | nav: Overview / Record data |
| student1@school.edu | student | Aarav Sharma, student id 1, nav: My records only |
| student3@school.edu | student | Rohan Mehta, id 3 — deliberately at-risk seed data |
| parent@school.edu | parent | linked only to student id 3 |

Newly created accounts (via People & classes) can log in immediately with the temporary
password you typed — a good end-to-end proof that creation actually worked.

## Verifying persistence

The SQLite DB is `backend/sams.db`. Capture counts before/after each write flow:

```bash
python3 -c "
import sqlite3; c=sqlite3.connect('backend/sams.db')
for t in ('attendance','marks','insight_reports'):
    print(t, c.execute(f'select count(*) from {t}').fetchone()[0])
"
```

Upsert checks that matter (the app upserts on `(student, subject, date)` for attendance
and `(assessment, student)` for marks):
- Save attendance twice for the same subject+date → total row count must NOT grow the
  second time, and the changed student's status must be overwritten.
- Save a mark twice for the same assessment+student → one row, score overwritten, and the
  subject's `assessments_count` must increment by 1 only.

Useful API probe (metrics reflect writes immediately):

```bash
T=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d 'username=admin@school.edu&password=Password123!' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $T" http://localhost:8000/api/insights/students/1/metrics
```

Route note: analytics endpoints are under `/api/insights/...` (e.g.
`/api/insights/at-risk`, `/api/insights/classes/{id}`), NOT `/api/analytics/...`.
Hitting a wrong API path returns the SPA `index.html` with HTTP 200 because of the
catch-all static mount — if a curl returns HTML, suspect a wrong path rather than a bug.

## Insights ("AI academic insights")

With no `OPENAI_API_KEY` set, `Generate insights` uses the deterministic rule engine.
The card footer should read "via rule-based engine" (not "language model") and each run
appends a row to `insight_reports` with `source='rules'`.

## Authorization boundaries worth re-testing

Type URLs directly in the address bar (client-side guards + API 403s):
- student/parent visiting `/records` or `/people` → redirected to `/`.
- student/parent visiting another student's `/students/:id` → page renders the plain
  text "Not allowed to access this student" and no student data.

## Known rough edge

On the admin Overview, the "Class analytics" class selector only refetches the tiles.
The "students who may need additional support" table and the "Students" table are
fetched once without a class filter (`/api/insights/at-risk` and `/api/students`), so
selecting a second class shows that class's tiles alongside the other class's students.
If you see cross-class rows there, this is likely that known gap rather than a new
regression.

## Devin Secrets Needed

None. `backend/.env` already holds `SECRET_KEY`, `SEED_DEMO_DATA`, `STATIC_DIR` and
`CORS_ORIGIN_REGEX`; no `OPENAI_API_KEY` is required (rule-based insights are the
default path).
