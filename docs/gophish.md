# Connecting the real GoPhish engine

MorphPhish ships with a built-in **mock** campaign engine (one-click launch; the app
delivers the mail and tracks events on its own landing page). You can instead delegate
delivery to a real **GoPhish** instance — it is bundled in `docker-compose.yml` and sits
behind the `CampaignProvider` adapter, so no app code changes are needed.

GoPhish becomes the *delivery engine*; MorphPhish stays the orchestration + analytics
layer. GoPhish sends the mail via a sending profile pointed at **Mailpit**, so nothing
leaves the lab, and only synthetic `@demo.example.com` targets are ever used.

## One-time setup

1. **Start the stack** (GoPhish is included):
   ```
   docker compose up -d
   ```
   GoPhish admin/API is on `http://localhost:3333`, its phishing server on `http://localhost:8080`.

2. **Get the admin password** GoPhish prints on first boot:
   ```
   docker compose logs gophish | grep -i "please login with the username admin"
   ```
   It logs a line like `Please login with the username admin and the password <random>`.

3. **Log in** at `http://localhost:3333` (user `admin`, that password). Change the password when prompted.

4. **Copy the API key**: GoPhish UI → **Account Settings** → *API Key*.

5. **Wire MorphPhish** — in `.env`:
   ```
   CAMPAIGN_PROVIDER=gophish
   GOPHISH_API_KEY=<the key you copied>
   # already set for the bundled instance:
   # GOPHISH_URL=http://gophish:3333
   # GOPHISH_PHISH_URL=http://localhost:8080
   # GOPHISH_VERIFY_TLS=false
   ```
   Also keep `EMAIL_PROVIDER` wiring; GoPhish uses its own sending profile (auto-created to point at Mailpit).

6. **Recreate the backend** so it picks up the env:
   ```
   docker compose up -d backend
   ```

## What a launch does now

Approve a scenario and **Launch** it as usual. Instead of sending the mail itself, the
backend calls GoPhish and **auto-creates** the resources it needs (idempotently by name):

- **Sending profile** `MorphPhish Mailpit` → `mailpit:1025`.
- **Email template** `MorphPhish Authorized Simulation` → the generated subject/body + a tracked `{{.URL}}` link and open tracker.
- **Landing page** `MorphPhish Safe Landing` → a plain awareness page (no credential capture), redirecting to the app.
- A **fresh group** per launch containing the single synthetic target.
- A **campaign** tying them together, launched immediately.

GoPhish delivers to Mailpit (`http://localhost:8025`) and tracks **opened / clicked** in
its own dashboard at `http://localhost:3333`. MorphPhish records the GoPhish campaign id
on its campaign. (Credential-capture and the teachable-moment debrief remain in the
MorphPhish sandbox on the mock path; the GoPhish landing page deliberately captures nothing.)

## Switching back

Set `CAMPAIGN_PROVIDER=mock` and `docker compose up -d backend`. The mock engine needs no
external service and is the default for development and tests.

## Safety notes

- Only synthetic recipients in `AUTHORIZED_EMAIL_DOMAINS`; the sending profile points at
  Mailpit, so no mail reaches real inboxes.
- The GoPhish landing page has credential/password capture **disabled**.
- GoPhish admin TLS is disabled for the local lab only (`gophish/config.json`); do not
  expose this instance outside the lab.
