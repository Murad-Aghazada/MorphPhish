# MorphPhish — Guide

A brief overview of what MorphPhish is, what it does, and how it works.

## What it is
MorphPhish is an **authorized, AI-assisted phishing-awareness simulation platform**. It
helps a security team measure and reduce human risk by running *simulated* phishing
campaigns against **synthetic employee personas** and turning the results into an
explainable, per-role risk picture plus targeted training. It is a training and
measurement tool — not an attack tool.

### Safety first (non-negotiable)
- **Synthetic data only** — personas use `@demo.example.com`; no real people are targeted.
- **No real credentials** — anything typed on a simulated sign-in page is immediately
  discarded: never stored, hashed, logged, or forwarded.
- **Contained delivery** — email goes only to the bundled **Mailpit** test inbox;
  recipients are restricted to `AUTHORIZED_EMAIL_DOMAINS`. No mail reaches real inboxes.
- **Human approval** — every scenario must be reviewed and approved before it can launch.

## The core flow
```
Personas → Risk score → Scenario (AI) → Human approval → Launch → Recipient events → Analytics → Training
```
1. **Personas** are imported from a (mock) HR source — name, role, department, language,
   privilege and data-access levels.
2. **Risk scoring** gives each persona an explainable 0–100 score: static exposure
   (role, department, data sensitivity, social/language exposure) plus a behavioural
   modifier from how they handled past simulations (falling for one raises it; reporting
   it lowers it; completed training lowers it).
3. **Scenario generation** drafts a role-appropriate lure (subject, body, pretext,
   landing page) via the configured LLM (or an offline mock). Safety-critical text is
   enforced by the platform, not the model.
4. **Approval** — an admin reviews the draft; only approved scenarios can launch.
5. **Launch** sends a realistic HTML email (with a tracking pixel) to the persona via
   Mailpit. The link leads to a realistic sign-in page.
6. **Events** are recorded as the recipient interacts: **Opened → Clicked → Submitted**,
   or **Reported** (the good outcome). Submitting/reporting ends the run and retires the
   link; a teachable-moment debrief is then shown.
7. **Analytics & training** aggregate everything into a funnel, a per-department/role
   risk map, and corrective training you can assign and track.

## The console (tabs)
- **Dashboard** — headline metrics and overall posture at a glance.
- **Employees** — the personas with risk scores; filter, sort, drill into a profile
  (explainable risk factors + operational context).
- **Simulations** — active runs: generate, edit, approve, launch, and watch outcomes;
  close stale no-response runs.
- **Archive** — finished runs, searchable by recipient, sortable by date.
- **Analytics** — the engagement funnel, open/click/submit/report rates, average
  response time, and risk distribution by department and role.
- **Training** — derived corrective topics per persona; assign and mark complete
  (completion feeds back into risk).

## Access
- The console is **gated by an admin login** (session token; demo/default is set via
  `ADMIN_USERNAME` / `ADMIN_PASSWORD`). Repeated failed logins are rate-limited.
- The **Mailpit inbox** (where simulation emails land) is reachable from the sidebar
  **Mail inbox ↗** link, behind the *same* login — no separate Mailpit credentials.

## How it's built
- **Backend:** FastAPI + SQLAlchemy (SQLite or Postgres), Alembic migrations.
- **Frontend:** React + Vite (single-page app), Recharts for the analytics.
- **Providers (pluggable adapters):** LLM (mock / OpenAI / Anthropic / Gemini / NVIDIA),
  HR (mock / REST), Campaign (mock / GoPhish), Email (mock / SMTP→Mailpit).
- **Defaults are safe/offline** (everything `mock`); live providers are opt-in via `.env`.

## Running it
- **Local/demo:** `docker compose up -d --build`, then open the frontend and sign in.
  See the project `README.md`.
- **Deployed (server/VPN/Cloudflare):** see `docs/deploy-vpn-proxy.md`.
- **API reference:** `docs/api.md`. Architecture: `docs/architecture.md`.

## One-line summary
Measure who in the organization is most at risk, prove it with safe simulated phishing,
and close the gap with targeted training — all on synthetic data, with real credentials
never touched.
