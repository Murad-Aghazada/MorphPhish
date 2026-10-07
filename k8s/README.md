# MorphPhish — temporary Kubernetes deployment

A self-contained deployment that lives entirely in the **`morphphish` namespace** and
serves the app at **https://morphphish.example.com** via ingress-nginx + cert-manager.
It does not touch cluster-scoped resources, so it never disturbs other workloads and is
removed with a single command.

```
Internet ──TLS──> ingress-nginx ──> frontend (nginx)
                                       ├── /            SPA
                                       ├── /api/        ──> backend  (FastAPI, SQLite on emptyDir)
                                       └── /mailpit/     ──> mailpit  (gated by the admin session)
                                                             backend ──SMTP:1025──> mailpit
```

- **Namespace-scoped**: one `kubectl delete namespace morphphish` wipes everything.
- **ClusterIP only**: no NodePorts; the single public entrypoint is the Ingress.
- **SQLite on emptyDir**: no database pod, no PVC/StorageClass, nothing persistent to clean up (demo data resets if the backend pod restarts).
- **Resource-capped**: small requests/limits so it can't starve neighbours.

## Prerequisites
- `kubectl` + `kustomize` (built into `kubectl apply -k`), access to the cluster.
- ingress-nginx controller and cert-manager with a ClusterIssuer (default assumed: `letsencrypt-prod`).
- A DNS A/AAAA record for `morphphish.example.com` pointing at the ingress load balancer.
- Docker Hub account (private repos supported).

## 1. Build and push the images
Build the frontend with the same-origin API base so nginx proxies `/api` internally:

```bash
export HUB=<your-dockerhub-user>
export TAG=0.1.0

docker build -t docker.io/$HUB/morphphish-backend:$TAG ./backend
docker build --build-arg VITE_API_URL=/api/v1 -t docker.io/$HUB/morphphish-frontend:$TAG ./frontend

docker login
docker push docker.io/$HUB/morphphish-backend:$TAG
docker push docker.io/$HUB/morphphish-frontend:$TAG
```

Keep the repos **private** on Docker Hub if you prefer; step 3 creates the pull secret.

## 2. Point kustomize at your images
Edit `k8s/kustomization.yaml` → set `DOCKERHUB_USER` and the tag in the `images:` block.
Also confirm the host in `k8s/ingress.yaml` and `k8s/configmap.yaml` matches your domain,
and the `cert-manager.io/cluster-issuer` annotation matches your ClusterIssuer.

## 3. Create the namespace and secrets (never committed to git)
```bash
kubectl create namespace morphphish

# App secrets — use real values. ADMIN_PASSWORD / APP_SECRET_KEY must not be defaults,
# or the backend intentionally refuses to start in production.
kubectl -n morphphish create secret generic morphphish-secrets \
  --from-literal=APP_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')" \
  --from-literal=ADMIN_USERNAME="admin" \
  --from-literal=ADMIN_PASSWORD="<strong-password>" \
  --from-literal=LLM_API_KEY="<your-gemini-api-key>"

# Private Docker Hub pull secret (referenced as imagePullSecrets: regcred).
kubectl -n morphphish create secret docker-registry regcred \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username="$HUB" \
  --docker-password="<dockerhub-token-or-password>"
```

## 4. Deploy
```bash
kubectl apply -k k8s/
kubectl -n morphphish rollout status deploy/backend
kubectl -n morphphish get pods,ingress
```
cert-manager provisions the TLS certificate within a minute or two (watch with
`kubectl -n morphphish get certificate`). Then open **https://morphphish.example.com**
and sign in with the admin credentials from the Secret. The Mailpit inbox is the
**Mail inbox ↗** link in the sidebar (same login — no separate Mailpit credentials).

## Update to a new build
```bash
# push a new TAG, bump it in kustomization.yaml, then:
kubectl apply -k k8s/
# or, same tag: kubectl -n morphphish rollout restart deploy/backend deploy/frontend
```

## Stop / remove completely
```bash
kubectl delete namespace morphphish
```
This deletes every object (Deployments, Services, Ingress, ConfigMap, Secrets, the
cert-manager Certificate and its TLS secret, and the pods' emptyDir data). Nothing is
left cluster-wide. Optionally remove the DNS record and the Docker Hub images.

## Notes
- **Single admin, coarse lockout**: with two proxy hops the client IP isn't reliable, so
  `TRUST_PROXY_HEADERS=false` and the login lockout counts failures globally (un-spoofable,
  but a flood can briefly lock the one admin out — it clears after `LOGIN_LOCKOUT_MINUTES`).
- **Scaling**: the backend is pinned to 1 replica because it uses SQLite. For a non-temporary
  deployment, switch `DATABASE_URL` to a Postgres service and raise replicas.
- **Email**: Mailpit is a test inbox; no mail leaves the cluster. Recipients are still
  restricted to `AUTHORIZED_EMAIL_DOMAINS`.
