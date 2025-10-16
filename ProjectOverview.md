# Google API Project — Background, Plan, and Repo Unification (Oct 16, 2025)

## Executive Summary

You have a working **Next.js frontend** (App Router, Tailwind, shadcn/ui) and a **Python backend** originally delivered via **Streamlit**. You want to: (1) publish behind a **Google-owned link** with access to users who signs up, and (2) **combine frontend + backend in one GitHub repo (database layer in Phase 2)** with a production deployment path (Google Cloud Run / App Hosting with IAP). The recommended target is a single repo with a clear separation of concerns, Dockerized services, and a CI/CD pipeline to Google Cloud. Short term, keep Python for Google Calendar logic and parsing; medium term, you can migrate selected endpoints into Next.js route handlers if desired.

---

## Background: What the “Google API Project” Is

**Purpose:** Build a scheduling assistant that lets users paste or chat free‑text, optionally parse with an LLM, review/edit a preview table, and then create/delete Google Calendar events with an undoable batch stack. The app must authenticate with Google, respect billing controls, and remain private to a controlled audience (Workspace).

**Inputs & Modes**

- **Chat mode** → parse free text into structured events.
- **Bulk paste / file upload** → parse dictionaries directly without LLM&#x20;
- **Inline edits** → user verifies fields before writing to Calendar.

**Core Operations**

- **Auth**: Google OAuth (Workspace gating).
- **Parse**: LLM or deterministic parser → `{title, date, time, description, location}`.
- **Validate**: date normalization, dedupe, conflict checks.
- **Write**: create Google Calendar events; capture IDs.
- **Undo/Manage**: delete or batch‑revert created sets; show session stats.
- **Billing/Usage**: gate LLM calls (OpenAI/Ollama), cache results, track per user/session.

---

## What You Planned vs. What You’ve Done

**Planned**

1. Ship a friendly **Next.js UI** with multiple input modes and previews.
2. Use **Google OAuth** and **Workspace allow‑list** so only employees can access.
3. Offer **LLM parsing**, billable step; otherwise accept structured paste/upload.
4. Maintain an **undo stack** and **session usage stats**.
5. Deploy privately on Google (custom link), ideally behind **Identity‑Aware Proxy (IAP)**.

**Done So Far**

- **Frontend** scaffolded (Next.js App Router) with pages for: `bulk-import`, `chat-parser`, `event-builder`, `manage-events`, `settings`, `help`.
- **UI components** (shadcn/ui) and **hooks** are in place; placeholder Firebase stub exists. But need to change it. Current have two different projects, front end and backend. I need to combine them as one.
- **Backend (Python/Streamlit)**: working logic for auth helpers, calendar create/delete flows, validation, LLM parsing experiments, and tests.
- **Docker learning** underway; desire to run everything with containers and deploy to a private Google URL.

---

## Current Architecture (as of now)

- **Frontend**: Next.js App Router, Tailwind, shadcn/ui, pages per workflow; no real server API yet (or mocked).
- **Backend**: Streamlit app with Python modules providing:
  - `auth.py` (Google auth helpers)
  - `calendar_methods.py` / `creating_calendar.py` (create/delete events)
  - `llm_parse.py` (text → structured events)
  - `validation.py` (field checks, normalization)
  - tests under `Tests/` verifying API and parser behavior

**Gaps**

- No stable HTTP API surface between frontend and backend.
- Streamlit is UI‑centric; you need a headless, idempotent **REST (or RPC) API**.
- Centralized auth/session model (workspace gating + user identity) needs to be enforced server‑side.

---

## Recommendation: Combine Repos, Keep Python Service, Add a Thin API Layer

Use a **single monorepo** with two top‑level apps:

```
repo-root/
├─ apps/
│  ├─ web/                # Next.js (your current frontend)
│  └─ api/                # Python FastAPI (headless backend)
├─ packages/              # (optional) shared code
├─ infra/                 # IaC, Docker, compose, Cloud Run config
├─ .github/workflows/     # CI/CD
└─ README.md
```

**Why this shape?**

- Keeps your proven Python calendar/LLM code.
- Gives the frontend a stable `/api/*` target.
- Dockerizes both for local dev and Cloud Run.
- Lets you add IAP at the perimeter and keep app‑level auth.

> **Note:** You can later fold selective endpoints into Next.js **route handlers** if you want a single runtime, but a Python API preserves existing tests and libraries with minimal churn.

---

## Backend: Minimal FastAPI that Wraps Your Existing Modules

**Key endpoints** (JWT‑protected, Google Workspace‑gated):

- `POST /v1/parse` → body: raw text or dicts; returns normalized event rows.
- `POST /v1/events:batchCreate` → body: events[]; returns created IDs and session token.
- `POST /v1/events:batchDelete` → body: ids[] or session token; returns counts.
- `GET  /v1/events` → optional filters; returns current user’s events.
- `GET  /v1/healthz` → liveness.

**Auth strategy**

- Prefer **NextAuth (Google)** on the web side. The frontend sends a signed session token.
- Backend validates via **signed JWT** (from NextAuth) **or** verifies Google ID token on the server. For simplicity, start with a shared HMAC JWT between web and API; upgrade to Google token checks later.

**FastAPI skeleton** (maps to your existing files):

```
apps/api/
├─ app.py                 # FastAPI app
├─ routers/
│  ├─ parse.py            # calls project_code/llm_parse.py
│  └─ events.py           # calls calendar_methods.py, creating_calendar.py
├─ services/
│  ├─ calendar.py         # thin adapters to Google API
│  └─ parser.py           # adapters to llm_parse, validation
├─ project_code/          # your current python modules (moved in)
├─ tests/                 # reuse & extend your Tests/
├─ requirements.txt
└─ Dockerfile
```

---

## Frontend: Call the API and Keep the Great UX

- Keep your pages and components.
- Add a client → server boundary:
  - `src/lib/api.ts` (fetch wrappers to FastAPI)
  - `src/app/api-proxy/*` (optional Next.js edge/middleware if you want same‑origin proxying)
- Use **NextAuth** with **Google Provider** and restrict sign‑in to your domain. The session token is attached on every API call (e.g., `Authorization: Bearer <jwt>`).

---

## Deployment Model on Google

**Private access first, custom link later:**

1. **Cloud Run (recommended)** for both services (`web` and `api`).
2. Put them behind a **HTTPS Load Balancer** with **IAP** enabled → only Workspace users can reach.
3. Map a **custom domain** (e.g., `calendar.yourdomain.com`).
4. Configure `web` → `NEXTAUTH_URL` accordingly; `api` URL set as `API_BASE_URL` in `web`.

**Alternative**: **Google App Hosting** for the `web` app (it’s designed for Next.js), and Cloud Run for `api`. You can still front both with IAP and a single domain.

---

## Local Dev (single command)

Use Docker Compose to bring up **Postgres** (if you add persistence later), **api**, and **web**:

```
infra/docker-compose.yml
services:
  api:
    build: ../apps/api
    env_file: ../apps/api/.env
    ports: ["8000:8000"]
  web:
    build: ../apps/web
    env_file: ../apps/web/.env
    ports: ["3000:3000"]
  # optional
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: appdb
    ports: ["5432:5432"]
```

---

## Security & Privacy Notes

- Enforce **Workspace domain allow‑list** in NextAuth `signIn` callback.
- IAP at the edge blocks non‑employees before your app is even reached.
- Backend validates **JWT** on every request; reject if missing/expired.
- Store secrets in **.env** locally and **Google Secret Manager** in prod.
- Scope Google Calendar API minimally (`calendar.events` as needed).

---

## Migration Plan (Streamlit → API)

1. **Freeze** Streamlit UI; extract pure functions from `streamlit_app/*` into `project_code/*` (most are already separate).
2. Wrap those functions in **FastAPI** routers.
3. Point the Next.js frontend to the new API endpoints and remove Streamlit from the critical path.
4. Keep your existing tests; add endpoint tests (pytest + httpx).

---

## Minimal Contracts (so both sides can evolve)

**Event schema (JSON)**

```json
{
  "title": "string",
  "startsAt": "ISO-8601",
  "endsAt": "ISO-8601 | null",
  "location": "string | null",
  "description": "string | null",
  "meta": { "source": "chat|paste|file", "confidence": 0.0 }
}
```

**API responses**

- `/v1/parse` → `{ events: Event[], warnings: string[], cost: { tokens?: number, usd?: number } }`
- `/v1/events:batchCreate` → `{ created: { id: string }[], undoToken: string }`
- `/v1/events:batchDelete` → `{ deleted: number }`

---

## Pros & Cons of Combining in One Repo

**Pros**

- Easier coordination, atomic PRs, shared issue tracker.
- One CI/CD to deploy both services.
- Clear contract tests between web and api.

**Cons**

- Repo grows large; needs discipline (folders, owners, CODEOWNERS).
- Mixed runtimes (Node + Python) mean two Docker images and two dependency graphs.

**Mitigation**

- Use workspaces (npm + pip), directory ownership, and pinned versions.

---

## Work Breakdown Structure (WBS) — High Level

1. **Repo Unification (Day 0–1)**
   - Create `apps/web` and move your Next.js tree in.
   - Create `apps/api` and move `project_code/*` + new FastAPI wrappers.
   - Add `infra/docker-compose.yml`, root README, and env examples.
2. **Auth & Security (Day 1–2)**
   - NextAuth with Google; domain allow‑list; JWT to API.
   - IAP plan doc for prod.
3. **API Endpoints (Day 2–4)**
   - `/v1/parse`, `/v1/events:batchCreate`, `/v1/events:batchDelete`, `/v1/events`.
   - Unit + integration tests.
4. **Frontend Wiring (Day 3–5)**
   - `src/lib/api.ts`; connect pages; session usage stats; undo UI.
5. **Docker & Local DX (Day 4–5)**
   - Dockerfiles for web & api; compose up; hot reload.
6. **CI/CD (Day 5–6)**
   - GitHub Actions → build, test, push images, deploy to Cloud Run.
7. **Prod Hardening (Day 6–7)**
   - IAP, custom domain, Secret Manager, error logging, metrics.

---

## Next Steps Checklist (Actionable)

-

---

## Final Thoughts on Combining Frontend & Backend

Do it. A single repository with a clean `web`/`api` split gives you the best of both worlds: keep Python where it shines (Calendar/LLM tooling) and let Next.js own the UX. Enforce contracts via tests, deploy each service to Cloud Run, and gate access with IAP + domain‑restricted NextAuth. This aligns with your privacy, billing, and maintainability goals and makes it trivial to evolve either side without blocking the other.

