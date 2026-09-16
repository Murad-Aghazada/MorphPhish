# API

Swagger is available at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health and provider mode |
| GET/POST | `/api/v1/employees` | List/create synthetic personas |
| GET/PATCH/DELETE | `/api/v1/employees/{id}` | Persona CRUD |
| GET/POST | `/api/v1/employees/{id}/risk` | View/recalculate deterministic risk |
| GET | `/api/v1/employees/{id}/context` | Synthetic operational context |
| GET | `/api/v1/scenarios` | List generated scenarios (newest first) |
| POST | `/api/v1/scenarios/generate` | LLM/mock structured scenario generation (persists as REVIEW_REQUIRED) |
| PATCH | `/api/v1/scenarios/{id}` | Edit an unapproved scenario; re-runs safety validation |
| POST | `/api/v1/scenarios/{id}/approve` | Approval gate |
| POST | `/api/v1/scenarios/{id}/reject` | Reject scenario |
| POST | `/api/v1/scenarios/{id}/launch` | **One-click launch**: create campaign + target + send; returns `simulation_url` |
| POST | `/api/v1/campaigns` | Create campaign from approved scenario (name optional; auto-derived) |
| POST | `/api/v1/campaigns/{id}/launch` | Launch an existing DRAFT campaign; returns `simulation_url` |
| GET | `/api/v1/simulation/{session_id}` | Safe landing context |
| POST | `/api/v1/simulation/{session_id}/event` | Store safe interaction event; password value discarded |
| GET | `/api/v1/analytics` | Aggregate database-driven metrics |
| GET | `/api/v1/campaigns/{id}/analytics` | Campaign metrics |
| GET | `/api/v1/recommendations` | Deterministic awareness recommendations |
| GET | `/api/v1/audit` | Recent administrative audit events |

Important errors: 404 unknown IDs/sessions, 409 invalid lifecycle transition or duplicates, 422 invalid/safety-rejected input, 503 unavailable external provider.
