# Student Academic Management System

A secure, role-based academic management platform for administrators, teachers, students and
parents, backed by a single centralised database and an AI layer that turns attendance, marks,
assignment and assessment data into performance trends, personalised recommendations and early
warnings for students who need additional support.

## Features

**Role-based access control (admin / teacher / student / parent)**

| Capability | Admin | Teacher | Student | Parent |
| --- | --- | --- | --- | --- |
| Manage classes, subjects, users | yes | no | no | no |
| Record attendance, marks, assignments | yes | own subjects only | no | no |
| View a student's academic record | all | own classes | own record | own children |
| Class analytics & at-risk report | all | own classes | no | no |
| AI insights for a student | all | own classes | own record | own children |

Authorisation is enforced server-side for every student-scoped endpoint
(`assert_can_view_student` / `assert_can_edit_student_records` in `backend/app/deps.py`), so the
UI never decides who may read what.

**AI academic insights**

1. `backend/app/ai/analytics.py` computes explainable metrics per student: attendance rate,
   per-subject averages and trend (improving / stable / declining), assignment completion,
   missing work, and a weighted risk score with human-readable reasons.
2. `backend/app/ai/insights.py` turns those metrics into a natural-language summary and three to
   five personalised study recommendations. When `OPENAI_API_KEY` is set an LLM generates them from
   the aggregated metrics only (no personal identifiers are sent); otherwise a deterministic
   rule-based generator produces the same output shape, so the product works offline and in CI.
3. Every generated report is stored in `insight_reports` for auditability and history.

**Security**

- Short-lived JWT access tokens held in memory; the refresh token is an HttpOnly, SameSite cookie.
- Changing a password or signing out bumps a token version, immediately invalidating every issued
  token for that account.
- `ENVIRONMENT=production` refuses to boot without a real `SECRET_KEY`.
- bcrypt password hashing, typed token validation.
- Server-enforced role checks, per-record ownership checks, and login/password-change audit logs.
- Security response headers, configurable CORS allow-list, secrets read from the environment.

## Stack

- Backend: FastAPI, SQLAlchemy 2, Pydantic v2, SQLite by default (PostgreSQL supported via
  `DATABASE_URL`).
- Frontend: React 19 + TypeScript + Vite, React Router, Recharts.

## Running locally

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # set SECRET_KEY (and DATABASE_URL / OPENAI_API_KEY if desired)
python -m app.seed            # optional demo dataset
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                   # http://localhost:5173
```

### Demo accounts (after `python -m app.seed`)

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@school.edu | Password123! |
| Teacher | teacher@school.edu | Password123! |
| Student | student1@school.edu | Password123! |
| Parent | parent@school.edu | Password123! |

The seed data intentionally includes two struggling students (low attendance and declining
scores) so the at-risk detection and recommendations are visible immediately.

## Tests and linting

```bash
cd backend && .venv/bin/python -m pytest && .venv/bin/ruff check .
cd frontend && npm run lint && npm run build
```

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/login` | OAuth2 password login; returns an access token and sets the refresh cookie |
| POST | `/api/auth/refresh` | Mint a new access token from the refresh cookie |
| POST | `/api/auth/logout` | Clear the refresh cookie and revoke outstanding tokens |
| GET | `/api/auth/me` | Current user |
| POST | `/api/classes`, `/api/subjects`, `/api/teachers`, `/api/students`, `/api/parents` | Admin provisioning |
| GET | `/api/students` | Scoped student list (admin: all, teacher: own classes, parent: children, student: self) |
| POST | `/api/attendance` | Bulk, idempotent attendance recording |
| POST | `/api/assessments`, `/api/marks` | Assessment creation and grading |
| POST | `/api/assignments`, `/api/submissions` | Assignment creation and submission tracking |
| GET | `/api/insights/students/{id}/metrics` | Explainable metrics for a student |
| POST | `/api/insights/students/{id}` | Generate AI summary + recommendations |
| GET | `/api/insights/students/{id}/history` | Previously generated reports |
| GET | `/api/insights/at-risk` | Students needing additional academic support |
| GET | `/api/insights/classes/{id}` | Class-level analytics |

## Using PostgreSQL

```bash
docker run -d --name sams-db -e POSTGRES_USER=sams -e POSTGRES_PASSWORD=sams \
  -e POSTGRES_DB=sams -p 5432:5432 postgres:16
# backend/.env
DATABASE_URL=postgresql+psycopg2://sams:sams@localhost:5432/sams
```

Tables are created on startup; introduce Alembic before running this in production.

## Single-origin deployment

The API can serve the built SPA so the whole system runs behind one port:

```bash
cd frontend && VITE_API_BASE_URL= npm run build
cd ../backend
# backend/.env
STATIC_DIR=../frontend/dist
SEED_DEMO_DATA=true          # demo data only; leave false in production
ENVIRONMENT=production       # enforces a real SECRET_KEY and Secure cookies
SECRET_KEY=<random-32-bytes>
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

When the frontend is hosted separately, set `CORS_ORIGINS` (or `CORS_ORIGIN_REGEX`) to its origin and
`CROSS_SITE_FRONTEND=true`, which switches the refresh cookie to `SameSite=None; Secure` so browsers
still send it on the cross-site refresh call. That combination requires HTTPS on both origins.

## Docker

```bash
docker build -t sams .
docker run -p 8000:8000 -e SECRET_KEY=$(openssl rand -hex 32) -e SEED_DEMO_DATA=true sams
# or, with PostgreSQL:
SECRET_KEY=$(openssl rand -hex 32) docker compose up --build
```

The image builds the SPA and serves it plus the API on `$PORT` (default 8000), so it runs as-is on
Render, Railway, Fly.io or any container host.

### Render

`render.yaml` is a ready-to-use blueprint: in the Render dashboard choose **New > Blueprint**, point
it at this repository and deploy. It provisions a managed PostgreSQL instance, generates
`SECRET_KEY`, and health-checks `/api/health`. Set `SEED_DEMO_DATA=false` once you have real data.

### Railway / Fly.io

Both detect the root `Dockerfile`. Set `ENVIRONMENT=production`, `SECRET_KEY` (and `DATABASE_URL`
when using a managed database); `postgres://` URLs are normalised automatically.
