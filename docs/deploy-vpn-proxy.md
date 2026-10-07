# Deploy

## Simplest: direct `http://IP:3000` (no proxy, no cluster, no domain)
If you just want it reachable quickly, skip Traefik/ArgoCD entirely — the compose stack
already serves the SPA, API and Mailpit on one port. On the Docker host:
```bash
cd MorphPhish && git pull
cp .env.example .env      # if you don't have one yet
```
Set these in `.env` (replace `<IP>` with the host IP you'll browse to, e.g. 84.247.143.190 or the VPN IP):
```ini
APP_ENV=production
APP_SECRET_KEY=<random 32+ chars>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong>
COOKIE_SECURE=false                  # required for plain HTTP, so the Mailpit gate works
FRONTEND_URL=http://<IP>:3000
BACKEND_URL=http://<IP>:3000
CORS_ORIGINS=http://<IP>:3000
LLM_PROVIDER=gemini
LLM_API_KEY=<key>
LLM_MODEL=gemini-flash-lite-latest
EMAIL_PROVIDER=smtp
SEED_ON_START=true
```
```bash
docker compose up -d --build
```
Open **http://<IP>:3000** and sign in. Make sure the host firewall allows inbound 3000.
Caveat: plain HTTP means credentials travel unencrypted — fine for a short internal
demo; use the domain + TLS section below if it needs to be properly public.

---

## With a domain + HTTPS: Docker on a VPN host, published via the cluster's Traefik

The app runs as the compose stack on a Docker host that is only on the VPN. The
public server is a **k3s node whose Traefik owns :80/:443**, so the domain is published
by adding a small routing shim to the cluster that forwards to the device. The
application itself never runs in the cluster.

```
browser ──HTTPS──> Traefik (k3s, TLS via cert-manager) ──VPN──> 10.13.2.3:3000
morphphish.baysarb.com                                            (frontend nginx)
  A -> 84.247.143.190                                             ├── /         SPA
                                                                  ├── /api/     → backend
                                                                  └── /mailpit/ → mailpit (gated)
```

Facts for this environment:
- Server public IP: **84.247.143.190** (IPv6 `2a02:c207:2324:3626::1`).
- Device (Docker host) VPN IP: **10.13.2.3**, port **3000**.
- Ingress: **Traefik** (k3s). TLS: cert-manager ClusterIssuer **letsencrypt**.
- `kubectl` on the server needs `sudo k3s kubectl` (or `KUBECONFIG=/etc/rancher/k3s/k3s.yaml`).

## 1. DNS
`morphphish.baysarb.com` → **A `84.247.143.190`** (optionally AAAA `2a02:c207:2324:3626::1`).
Let's Encrypt (HTTP-01) needs this resolving before the cert can be issued.

## 2. On the VPN'd Docker host (10.13.2.3)
```bash
git clone https://github.com/iqulzade/MorphPhish && cd MorphPhish
cp .env.example .env
```
Edit `.env`:
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
EMAIL_PROVIDER=smtp
SEED_ON_START=true
```
Start it (overlay publishes only :3000 on the host):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/        # expect 200
```

## 3. On the server — verify reachability, then add the route
```bash
# Traefik (a pod) will connect to the device; first confirm the node can reach it:
curl -s -o /dev/null -w "%{http_code}\n" http://10.13.2.3:3000          # expect 200
sudo k3s kubectl get ingressclass                                       # confirm name is "traefik"
sudo k3s kubectl get clusterissuer                                      # confirm "letsencrypt" is Ready
```
Then apply the routing shim (`deploy/cluster-route/morphphish-route.yaml` — a
selectorless Service + EndpointSlice → `10.13.2.3:3000` and a Traefik Ingress with TLS):

**This cluster is a full app-of-apps GitOps setup** (project `infra`), so register the
route as an ArgoCD Application rather than `kubectl apply` (which would be pruned). Use
`deploy/cluster-route/argocd-application.yaml`:
- Add it to your infra GitOps repo alongside the other `argocd-*` Application
  definitions, commit, and ArgoCD creates it. It syncs only `morphphish-route.yaml`
  (the Service + EndpointSlice + Ingress) into the `morphphish-route` namespace.
- Set `spec.project` to an AppProject that permits the source repo and the destination
  namespace. If `infra` only allows your own GitLab, copy `morphphish-route.yaml` into
  your GitOps repo and point the Application's `source` there instead of the GitHub repo.

Verify the cert issues (a minute or two) and the site answers:
```bash
sudo k3s kubectl -n morphphish-route get ingress,endpointslice
sudo k3s kubectl -n morphphish-route get certificate        # READY should become True
curl -sI https://morphphish.baysarb.com | head -n1          # expect HTTP/2 200
```
Open **https://morphphish.baysarb.com**, sign in, and the Mailpit inbox is the
**Mail inbox ↗** link in the sidebar (same login).

## Update / redeploy to the latest build
If you deployed an earlier build, pull and rebuild **with the prod overlay** and make
sure `.env` has the step-2 values (especially `APP_ENV=production` and the three
`https://morphphish.baysarb.com` URLs, or the Mailpit gate and sim links misbehave):
```bash
# on the device
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps        # only the frontend should publish a host port (3000)
```

## Stop / remove completely
```bash
# cluster route: delete from the GitOps repo (ArgoCD prunes it), or:
sudo k3s kubectl delete namespace morphphish-route
# on the device:
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
# optionally remove the DNS record.
```

## Notes
- **Does not disturb other services**: the shim is its own namespace and one extra
  Traefik host rule; it doesn't touch existing routes. Traefik already multiplexes
  many hosts on 80/443.
- **Must be HTTPS**: `APP_ENV=production` marks the session cookie `Secure`; the Mailpit
  gate relies on it. Traefik terminates TLS, so this holds.
- **Login lockout is global/coarse** (two proxy hops hide the real client IP) —
  un-spoofable, but a flood briefly locks the single admin out; clears after
  `LOGIN_LOCKOUT_MINUTES`.
- **If Traefik can't reach the device** even though the node can, it's pod-egress to the
  VPN subnet — tell me and we'll adjust (hostNetwork solver or a node route).
- The compose database is Postgres with a volume; `down -v` wipes it.
