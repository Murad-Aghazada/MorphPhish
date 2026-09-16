# MorphPhish

Authorized, role-oriented, AI-assisted phishing-awareness simulation prototype using synthetic employee/context data. It implements the full flow from persona → explainable risk → contextual scenario generation → safety validation → admin approval → campaign → safe landing events → PostgreSQL analytics → React dashboard.

## Stack
FastAPI, SQLAlchemy, PostgreSQL, Alembic, React/Vite, Recharts, Docker Compose, provider adapters for LLM/GoPhish/SMTP, and pytest.

## Safety properties
- synthetic data by default;
- human approval required before campaign execution;
- no malware/payload generation;
- external SMTP is domain allow-listed;
- real password values are never needed and are immediately discarded if submitted to the simulation endpoint;
- audit logs exclude secrets;
- mock mode is the default.

## Quick start
```bash
cp .env.example .env
docker compose up --build
```
The backend container automatically runs Alembic and synthetic seeding.

URLs:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Mailpit UI (when SMTP provider is enabled for local testing): http://localhost:8025

## Provider configuration
Default: `LLM_PROVIDER=mock`, `CAMPAIGN_PROVIDER=mock`, `EMAIL_PROVIDER=mock`.
For OpenAI set `LLM_PROVIDER=openai` and `LLM_API_KEY`. For an approved GoPhish lab set `CAMPAIGN_PROVIDER=gophish`, `GOPHISH_URL`, and `GOPHISH_API_KEY`; see `gophish/README.md`. For local Mailpit set `EMAIL_PROVIDER=smtp`, `SMTP_HOST=mailpit`, `SMTP_PORT=1025`; recipients still must match `AUTHORIZED_EMAIL_DOMAINS`.

## Local backend development
```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./dev.db alembic upgrade head
DATABASE_URL=sqlite:///./dev.db python -m app.seed
DATABASE_URL=sqlite:///./dev.db uvicorn app.main:app --reload
```

## Frontend development
```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

## Tests
```bash
cd backend
pytest -q
python -m compileall app tests
cd ../frontend
npm install
npm run build
```

## Database migration and seed
Docker runs `alembic upgrade head` and `python -m app.seed` automatically. The seed is idempotent and creates six clearly synthetic personas, risk profiles/context, plus one historical synthetic campaign so charts are immediately meaningful.

## Architecture and security
See `docs/architecture.md`, `docs/security.md`, `docs/api.md`, `docs/demo.md`, and `docs/presentation-notes.md`.

## Troubleshooting
- Database startup: wait for the Postgres healthcheck; backend starts only after it passes.
- LLM 503: use mock mode or provide a valid API key/provider configuration.
- GoPhish 503: confirm the API URL/key and pre-created authorized GoPhish resources.
- SMTP rejection: ensure the recipient domain is listed in `AUTHORIZED_EMAIL_DOMAINS`.
- Browser CORS: add the exact frontend origin to `CORS_ORIGINS`.
