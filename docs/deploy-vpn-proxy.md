# Deploy

The app runs as the compose stack on the VPN host **10.13.2.3** and serves the SPA,
API and Mailpit on one port (**3000**). Two ways to reach it from outside.

## A. App config on the device (10.13.2.3) — do this first
```bash
cd MorphPhish && git pull
cp .env.example .env      # if you don't have one yet
```
Set in `.env` (use the address users will actually open — see options B1/B2 for what to put):
```ini
APP_ENV=production
APP_SECRET_KEY=<random 32+ chars>      # not "change-me*"
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong>                 # not "root"
COOKIE_SECURE=false                     # required for plain HTTP, so the Mailpit gate works
FRONTEND_URL=http://<public-address>
BACKEND_URL=http://<public-address>
CORS_ORIGINS=http://<public-address>
LLM_PROVIDER=gemini
LLM_API_KEY=<key>
LLM_MODEL=gemini-flash-lite-latest
EMAIL_PROVIDER=smtp
SEED_ON_START=true
```
```bash
docker compose up -d --build
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/   # expect 200
```
`<public-address>` is whatever the browser hits: `10.13.2.3:3000` (B1) or
`84.247.143.190:8080` / `morphphish.baysarb.com:8080` (B2).

## B1. Direct, if the device port is reachable
If `10.13.2.3:3000` is reachable from where you browse (e.g. on the VPN), just open
**http://10.13.2.3:3000**. Set the three URLs above to `http://10.13.2.3:3000`. Done.

## B2. Reverse proxy on the public server (reach it from the internet)
Put a tiny proxy on the public server (84.247.143.190) that forwards to the device.
Traefik owns 80/443 there, so this uses **8080**.
```bash
# on the public server (Docker is installed there)
cd MorphPhish/deploy/server-proxy
# nginx.conf already targets 10.13.2.3:3000 — edit it if the device IP/port differ
docker compose up -d
```
Now it's reachable at **http://84.247.143.190:8080**. Set the three URLs on the device
to `http://84.247.143.190:8080` (or the domain, below) and `docker compose up -d --build`
again so links/cookies match. Make sure inbound **8080** is open on the server firewall.

Remove the proxy anytime: `cd deploy/server-proxy && docker compose down`.

## C. Cloudflare Tunnel — clean https://morphphish.baysarb.com, free cert, no open ports
The zone `baysarb.com` is on Cloudflare, so a tunnel is the cleanest public option: a
real cert, no inbound ports, and nothing in the k3s/Traefik stack. Connector config is
in `deploy/cloudflared/`.

1. Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a tunnel** →
   connector **Cloudflared** → name `morphphish` → Save. Copy the **token** from the
   install command shown (the long string after `--token`).
2. Same tunnel → **Public Hostname → Add**:
   - Subdomain `morphphish`, Domain `baysarb.com`
   - Service **HTTP**, URL **`10.13.2.3:3000`** (the app's VPN/LAN IP — works from any
     connector host). Use `host.docker.internal:3000` only if the connector runs on the
     same machine as the app under Docker Desktop. Save — this creates the proxied DNS record.
   - If it warns that a `morphphish` DNS record already exists, delete that old A record first.
3. Run the connector (anywhere with internet egress that can reach `10.13.2.3:3000`):
   ```bash
   cd MorphPhish/deploy/cloudflared
   # Create .env as UTF-8 (NOT PowerShell `echo >`, which writes UTF-16 and breaks Compose):
   #   Linux/mac:  printf 'TUNNEL_TOKEN=%s\n' '<paste-token>' > .env
   #   Windows PS: Set-Content .env 'TUNNEL_TOKEN=<paste-token>' -Encoding ascii -NoNewline
   docker compose up -d
   docker compose logs --tail=20 cloudflared     # expect "Registered tunnel connection"
   ```
4. Point the app at the HTTPS hostname and rebuild (drop COOKIE_SECURE — it's real TLS now):
   ```ini
   APP_ENV=production
   FRONTEND_URL=https://morphphish.baysarb.com
   BACKEND_URL=https://morphphish.baysarb.com
   CORS_ORIGINS=https://morphphish.baysarb.com
   ```
   ```bash
   cd ~/MorphPhish && docker compose up -d --build
   ```
5. Open **https://morphphish.baysarb.com**. Then retire the plain-HTTP proxy and its
   firewall rule — the tunnel needs no inbound ports:
   ```bash
   cd deploy/server-proxy && docker compose down
   ```

## Domain (optional, no certificate needed)
Point DNS **A `morphphish.baysarb.com` → 84.247.143.190**, then open
**http://morphphish.baysarb.com:8080** (set the device's three URLs to that). The `:8080`
is needed because Traefik holds port 80. A *clean* `https://morphphish.baysarb.com`
(no port, with a cert) is only possible through that Traefik — ask me and I'll add the
small route for it; it's the one thing that must live in the cluster.

## Update / remove
```bash
# device: update
git pull && docker compose up -d --build
# device: remove everything
docker compose down -v
# server: remove the proxy
cd deploy/server-proxy && docker compose down
```

## Notes
- **Plain HTTP** means credentials travel unencrypted — fine for a short internal/VPN
  demo. For real public use, get the `https://…` Traefik route.
- `COOKIE_SECURE=false` is what makes the Mailpit gate work over HTTP.
- The compose database is Postgres with a volume; `down -v` wipes it.
