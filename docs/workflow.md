# Git Repository Structure & Workflow

Week 1 deliverable: a defined repository layout and a lightweight branching workflow the team follows.

## Repository layout
```
MorphPhish/
├── backend/            FastAPI service, SQLAlchemy models, Alembic migrations, pytest
│   ├── app/            application code (api, services, models, risk, llm, integrations)
│   ├── alembic/        database migrations
│   ├── scripts/        container entrypoint (start.sh)
│   └── tests/          pytest suite
├── frontend/           React + Vite single-page dashboard
├── gophish/            GoPhish integration boundary notes
├── docs/               architecture, security, api, demo, RoE, workflow
├── docker-compose.yml  db + mailpit + backend + frontend
├── .env.example        template config (copy to .env; .env is never committed)
└── fisinq-4-heftelik-plan.md   project brief + 4-week plan
```

## Branching model
- `main` — always green: tests pass, `docker compose up` works. No direct pushes for shared work.
- `feature/<short-name>` — one branch per subtask (e.g. `feature/risk-profiling`, `feature/llm-prompts`).
- `fix/<short-name>` — bug fixes.
- Open a pull request into `main`; at least one teammate reviews before merge.

## Commit conventions
- Present-tense, scoped summaries: `backend: add employee delete cascade`, `frontend: register vite react plugin`.
- Keep commits focused; don't mix unrelated changes.

## Definition of done (per subtask)
1. Code + migration (if schema changed) committed on a feature branch.
2. `cd backend && pytest -q` passes; `python -m compileall app tests` clean.
3. `cd frontend && npm run build` succeeds (when frontend touched).
4. Docs updated if behavior or setup changed.
5. PR reviewed and merged into `main`.

## Never commit
`.env`, real credentials, real employee/PII data, `node_modules/`, `.venv/`, build output, `*.db`.
(Enforced by `.gitignore`; verify with `git status` before every commit.)

## Progress
- **Week 1 — done:** git + workflow, RoE draft, Docker dev env, PostgreSQL schema, synthetic data.
- **Week 2 — done:** HR data layer via adapter pattern (`MockHRAdapter` + `RestHRAdapter` stub, `POST /hr/sync`); explainable risk-profile schema weighted across role / department / language / data access / social exposure; profile endpoints incl. `/employees/{id}/profile`; shared prompt-template layer driving all providers; LLM integration for **mock / OpenAI (GPT) / Anthropic (Claude)**; difficulty-aware, multilingual (AZ / EN / RU) generation.

## Team roles (fill in)
| Module | Owner |
|---|---|
| Risk profiling + data model | _TBD_ |
| LLM scenario generation | _TBD_ |
| Operational context + sandbox | _TBD_ |
| Analytics + dashboard | _TBD_ |
| Ethics / RoE / documentation | _TBD_ |
