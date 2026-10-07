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

## 3. On the public server (nginx) — without disturbing existing sites
This only *adds* a name-based virtual host for `morphphish.baysarb.com`; it shares
ports 80/443 with the other sites via normal virtual hosting and does not change them.
Two rules keep it safe: **always `nginx -t` before reloading** (a failed test means you
simply don't reload, and the running config is untouched — reload is zero-downtime),
and **never `restart`** (use `reload`).

```bash
# 0) back up the current config (instant rollback if needed)
sudo cp -a /etc/nginx /etc/nginx.bak.$(date +%F)

# 1) pre-flight: make sure nothing already claims this host
sudo grep -rn "morphphish.baysarb.com" /etc/nginx/        # expect: no matches
sudo nginx -T | grep -c "server_name _.*default_server"   # just informational

# 2) drop in the vhost and set the device's VPN IP
sudo cp deploy/nginx-morphphish.conf /etc/nginx/conf.d/morphphish.conf
sudo sed -i 's/DEVICE_VPN_IP/<device-vpn-ip>/' /etc/nginx/conf.d/morphphish.conf

# 3) TEST FIRST — only reload if it says "syntax is ok / test is successful"
sudo nginx -t
sudo systemctl reload nginx

# 4) get the TLS cert. certonly does NOT rewrite your other vhosts; it only obtains
#    the cert (the nginx plugin handles the challenge and reverts).
sudo certbot certonly --nginx -d morphphish.baysarb.com
```
Then uncomment the HTTPS block at the bottom of `morphphish.conf` (it references the
cert paths certbot just created) and turn the port-80 block into a redirect — both are
pre-written in the file — then `sudo nginx -t && sudo systemctl reload nginx` again.

> Prefer the one-shot `sudo certbot --nginx -d morphphish.baysarb.com`? It also works
> and auto-adds the 443 block, but it *edits* nginx config in place. With the backup from
> step 0 and `nginx -t` as the gate, it's still safe; `certonly` is just the most hands-off.

Open **https://morphphish.baysarb.com** and sign in with the admin credentials. The
Mailpit inbox is the **Mail inbox ↗** link in the sidebar (same login).

### If anything looks wrong
```bash
sudo rm /etc/nginx/conf.d/morphphish.conf   # remove just this vhost
sudo nginx -t && sudo systemctl reload nginx
# or full rollback: sudo rm -rf /etc/nginx && sudo mv /etc/nginx.bak.<date> /etc/nginx && sudo systemctl reload nginx
```

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
