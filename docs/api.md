# API

Swagger is available at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health and provider mode |
| GET/POST | `/api/v1/employees` | List/create synthetic personas |
| GET | `/api/v1/hr/source` | Preview raw records from the HR data layer (adapter) |
| POST | `/api/v1/hr/sync` | Import/update employees from the HR adapter (idempotent upsert) |
| GET/PATCH/DELETE | `/api/v1/employees/{id}` | Persona CRUD |
| GET/POST | `/api/v1/employees/{id}/risk` | View/recalculate deterministic risk |
| GET | `/api/v1/employees/{id}/context` | Synthetic operational context |
| GET | `/api/v1/employees/{id}/profile` | Persona + risk (explainable factors) + context in one call |
| GET | `/api/v1/scenarios` | List generated scenarios (newest first) |
| POST | `/api/v1/scenarios/generate` | LLM/mock structured scenario generation (persists as REVIEW_REQUIRED) |
| PATCH | `/api/v1/scenarios/{id}` | Edit an unapproved scenario; re-runs safety validation |
| POST | `/api/v1/scenarios/{id}/approve` | Approval gate |
| POST | `/api/v1/scenarios/{id}/reject` | Reject scenario |
| POST | `/api/v1/scenarios/{id}/regenerate` | Regenerate the message **in place** (same scenario id; resets to REVIEW_REQUIRED) |
| POST | `/api/v1/scenarios/{id}/launch` | **One-click launch** (requires admin HTTP Basic auth): create campaign + target + send; returns `simulation_url` |
| GET | `/api/v1/scenarios/{id}/result` | Per-target outcome of a launched scenario (which funnel stages each recipient reached) |
| POST | `/api/v1/campaigns` | Create campaign from approved scenario (name optional; auto-derived) |
| POST | `/api/v1/campaigns/{id}/launch` | Launch an existing DRAFT campaign (requires admin HTTP Basic auth); returns `simulation_url` |
| GET | `/api/v1/simulation/{session_id}` | Safe landing context (410 once the session is completed — the link is retired) |
| GET | `/api/v1/simulation/{session_id}/pixel.gif` | Email-open tracking pixel: records `email_opened`, returns a 1x1 GIF |
| POST | `/api/v1/simulation/{session_id}/event` | Store safe interaction event (idempotent per session + event_type); password value discarded |
| GET | `/api/v1/analytics` | Human-risk map: funnel + per-department & per-role engagement + risk distribution |
| GET | `/api/v1/campaigns/{id}/analytics` | Flat per-campaign metrics (delivery/open/click/submission/reporting + avg response) |
| GET | `/api/v1/recommendations` | Deterministic awareness recommendations |
| GET | `/api/v1/audit` | Recent administrative audit events |

Important errors: 404 unknown IDs/sessions, 409 invalid lifecycle transition or duplicates, 422 invalid/safety-rejected input, 503 unavailable external provider.

## `/analytics` response shape (Week 4)

```jsonc
{
  "campaigns": 5, "targets": 5, "delivered": 5,
  "delivery_rate": 100.0, "open_rate": 40.0, "click_rate": 60.0,
  "submission_rate": 20.0, "reporting_rate": 20.0,
  "average_response_time_seconds": 42.0,
  "funnel": [ { "stage": "delivered", "count": 5, "rate": 100.0 }, … ],   // delivered→opened→clicked→submitted→reported, rate = % of delivered
  "by_department": [ { "key": "Finance", "employees": 3, "average_risk": 81.8,
                       "delivered": 2, "click_rate": 50.0, "submission_rate": 50.0,
                       "reporting_rate": 0.0, "average_response_time_seconds": 30.1 }, … ],  // sorted by average_risk desc
  "by_role": [ { "key": "DevOps Engineer", … same metric set … }, … ],
  "risk_distribution": [ { "level": "critical", "count": 4 }, { "level": "high", … }, … ]  // always the 4 ordered levels
}
```

## Email delivery (Week 4)

`launch` sends the simulation email through the configured email provider as a realistic
**multipart/alternative** message: a plain-text part plus a branded HTML part with a
styled call-to-action button (`build_email_html`). The From display name is the impersonated
team and the subject/CTA are localized per persona (AZ/EN/RU); the From address stays the
authorized `SMTP_FROM`. Set `EMAIL_PROVIDER=smtp` to deliver to the bundled **Mailpit** test
inbox (the local stand-in for Mailtrap) at `http://localhost:8025`, which renders the HTML in
full; recipients are constrained to `AUTHORIZED_EMAIL_DOMAINS`. `EMAIL_PROVIDER=mock` (the test
default) records nothing externally.

The HTML email embeds a 1x1 **tracking pixel** (`…/pixel.gif`) so viewing the message records
`email_opened` — the funnel's *Opened* stage — when the mail client loads remote images.
(Mailpit may need "load remote content" enabled.) Following the link records *Clicked* and, since
reaching the page implies the email was opened, also backfills *Opened*, so the funnel stays
monotonic.

The landing page (`/simulate/{session_id}`) is a realistic sign-in page with no upfront
disclosure — following the link records the click, and the teachable-moment debrief (safety
disclosure + red flags) appears only after the person submits or reports. The submitted value
is discarded as always. Submitting or reporting **completes** the session: the backend then
retires the link (`GET /simulation/{session_id}` returns **410**), so the same URL cannot be
reused — the landing shows a neutral "this link is no longer active" page.
