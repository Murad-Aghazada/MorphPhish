# Deploy: Docker on a VPN host, public via a server reverse proxy

This is the lightweight path that avoids the Kubernetes cluster (and ArgoCD) entirely:
run the compose stack on a Docker host that is only on the VPN, and let the public
server's nginx forward the domain to it.

```
browser ──HTTPS──> server nginx (TLS) ──VPN──> device:3000 (frontend nginx)
morphphish.baysarb.com                           ├── /         SPA
  A record -> server public IP                   ├── /api/     → backend
                                                  └── /mailpit/ → mailpit (session-gated)
```

Only the frontend's `:3000` is exposed on the device; the backend, Postgres and
Mailpit stay on the internal compose network.

## 1. DNS
Create an A record: `morphphish.baysarb.com` → **the public server's** IP (not the
device — the device has no public address).

## 2. On the VPN'd Docker host
```bash
git clone https://github.com/iqulzade/MorphPhish && cd MorphPhish
cp .env.example .env
```
Edit `.env` — the essentials for a public HTTPS deployment:
```ini
APP_ENV=production                       # secure cookies + HSTS; refuses default secrets
APP_SECRET_KEY=<python -c "import secrets;print(secrets.token_urlsafe(32))">
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>         # must NOT be the default, or the backend won't boot
FRONTEND_URL=https://morphphish.baysarb.com
BACKEND_URL=https://morphphish.baysarb.com
CORS_ORIGINS=https://morphphish.baysarb.com
TRUST_PROXY_HEADERS=false                # two proxy hops -> coarse (global) login lockout, un-spoofable

LLM_PROVIDER=gemini
LLM_API_KEY=<your-gemini-key>
LLM_MODEL=gemini-flash-lite-latest

EMAIL_PROVIDER=smtp                      # deliver simulation mail to the bundled Mailpit
SEED_ON_START=true                       # demo personas + scenarios on first boot
```
Start it (production overlay unpublishes everything but :3000):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/        # 200
```

## 3. On the public server (nginx)
Copy `deploy/nginx-morphphish.conf` to `/etc/nginx/conf.d/morphphish.conf`, set
`DEVICE_VPN_IP` to the Docker host's VPN address, then:
```bash
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d morphphish.baysarb.com     # obtains the cert and adds the 443 block + redirect
```
Open **https://morphphish.baysarb.com** and sign in with the admin credentials. The
Mailpit inbox is the **Mail inbox ↗** link in the sidebar (same login).

## Update
```bash
# on the device
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Stop / remove completely
```bash
# on the device
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v   # containers + volumes
# on the server
sudo rm /etc/nginx/conf.d/morphphish.conf && sudo systemctl reload nginx
# optionally: remove the DNS record and the Let's Encrypt cert (certbot delete)
```

## Notes
- **Must be HTTPS**: `APP_ENV=production` marks the session cookie `Secure`, so the
  Mailpit gate only works over TLS. (The console login itself uses a bearer token and
  would work over plain HTTP, but the Mailpit cookie would not be sent.)
- **Login lockout is global/coarse** here: with two proxy hops the real client IP
  isn't reliable, so failed sign-ins are counted across all sources (un-spoofable, but
  a flood briefly locks the single admin out; clears after `LOGIN_LOCKOUT_MINUTES`).
- **No mail leaves the cluster**: Mailpit is a test inbox and recipients are still
  limited to `AUTHORIZED_EMAIL_DOMAINS`.
- The database here is the compose Postgres (with a volume); `down -v` wipes it.
- The overlay uses the `!reset` tag to unpublish the backend/db/Mailpit host ports,
  which needs Docker Compose ≥ v2.24. On older Compose it errors — drop the overlay
  (those ports are then published on the device, but it's VPN-only and the API is
  still auth-gated), or remove those `ports:` from the base file.
