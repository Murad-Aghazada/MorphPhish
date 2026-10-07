#!/usr/bin/env bash
# Build + push the MorphPhish images (public Docker Hub) and apply the manifests.
# Usage: docker login && HUB=<dockerhub-user> [TAG=0.1.0] ./k8s/deploy.sh
set -euo pipefail

: "${HUB:?set HUB to your Docker Hub user, e.g. HUB=myuser ./k8s/deploy.sh}"
TAG="${TAG:-0.1.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# The admin/Gemini secret must exist first (see k8s/README.md step 1), or the
# backend pod crash-loops on purpose (production refuses default credentials).
kubectl create namespace morphphish --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n morphphish get secret morphphish-secrets >/dev/null 2>&1; then
  echo "ERROR: secret 'morphphish-secrets' not found in namespace morphphish." >&2
  echo "Create it first — see k8s/README.md step 1." >&2
  exit 1
fi

echo ">> building images (docker.io/$HUB, tag $TAG)"
docker build -t "docker.io/$HUB/morphphish-backend:$TAG" "$ROOT/backend"
docker build --build-arg VITE_API_URL=/api/v1 -t "docker.io/$HUB/morphphish-frontend:$TAG" "$ROOT/frontend"

echo ">> pushing images"
docker push "docker.io/$HUB/morphphish-backend:$TAG"
docker push "docker.io/$HUB/morphphish-frontend:$TAG"

echo ">> applying manifests"
# Render kustomize, then substitute the Docker Hub user and tag (keeps the tracked
# files unmodified). Requires the kustomize built into kubectl.
kubectl kustomize "$ROOT/k8s" \
  | sed -e "s#docker.io/DOCKERHUB_USER#docker.io/$HUB#g" \
        -e "s#\(morphphish-\(backend\|frontend\)\):0.1.0#\1:$TAG#g" \
  | kubectl apply -f -

kubectl -n morphphish rollout status deploy/backend
kubectl -n morphphish rollout status deploy/frontend
echo ">> done. Watch TLS: kubectl -n morphphish get certificate"
