"""Admin authentication for the MorphPhish console.

Full-gate model: every admin/API route (everything except /health, /auth/login
and the recipient-facing /simulation/* endpoints) requires a valid session.

Sessions are stateless, signed tokens — an HMAC-SHA256 over APP_SECRET_KEY with
an embedded expiry — so no extra dependency or token store is needed. The same
dependency still accepts HTTP Basic (root/root) for scripted/back-compat callers.

Login is rate-limited with a lockout window to blunt brute-force against the
admin password. The counter is in-memory (per process), which suits the
single-host deployment; a multi-replica deployment would move it to a shared store.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from .core.config import settings

# ---------------------------------------------------------------- tokens
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def _sign(body: str) -> str:
    return _b64e(hmac.new(settings.app_secret_key.encode(), body.encode(), hashlib.sha256).digest())

def make_token(sub: str, ttl_minutes: int | None = None) -> str:
    ttl = settings.token_ttl_minutes if ttl_minutes is None else ttl_minutes
    payload = {"sub": sub, "exp": int(time.time()) + ttl * 60}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"

def verify_token(token: str) -> str | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sign(body)):   # tamper / wrong-secret
        return None
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):  # expired
        return None
    return payload.get("sub") or None

def check_credentials(username: str, password: str) -> bool:
    return (secrets.compare_digest(username or "", settings.admin_username)
            and secrets.compare_digest(password or "", settings.admin_password))

# ---------------------------------------------------------------- login rate limit / lockout
_LOGIN: dict[str, dict] = {}  # ip -> {"fails": int, "locked_until": float}

def reset_rate_limit():
    """Test hook — clear the in-memory login throttle."""
    _LOGIN.clear()

def client_ip(request: Request) -> str:
    """Best-effort client identity for the login throttle.

    X-Forwarded-For is only honoured when TRUST_PROXY_HEADERS is set (i.e. the
    backend sits behind our reverse proxy), and then we take the LAST entry — the
    one the trusted proxy appended — because any entries to its left are supplied
    by the client and are spoofable. When not behind a trusted proxy we ignore the
    header entirely and use the peer address, so the lockout can't be evaded by
    forging X-Forwarded-For."""
    if settings.trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if parts:
                return parts[-1]
    return request.client.host if request.client else "unknown"

def login_guard_check(ip: str):
    rec = _LOGIN.get(ip)
    if rec and rec["locked_until"] > time.time():
        wait = int(rec["locked_until"] - time.time()) + 1
        raise HTTPException(429, f"Too many failed sign-in attempts. Try again in ~{wait // 60 + 1} min.",
                            headers={"Retry-After": str(wait)})

def login_record_failure(ip: str):
    rec = _LOGIN.setdefault(ip, {"fails": 0, "locked_until": 0.0})
    rec["fails"] += 1
    if rec["fails"] >= settings.login_max_attempts:
        rec["locked_until"] = time.time() + settings.login_lockout_minutes * 60
        rec["fails"] = 0

def login_record_success(ip: str):
    _LOGIN.pop(ip, None)

# ---------------------------------------------------------------- dependency
_basic = HTTPBasic(auto_error=False)

def require_auth(request: Request, basic: HTTPBasicCredentials | None = Depends(_basic)) -> str:
    """Accept a bearer session token (primary) or HTTP Basic (back-compat)."""
    authz = request.headers.get("authorization", "")
    if authz.lower().startswith("bearer "):
        sub = verify_token(authz[7:].strip())
        if sub:
            return sub
        raise HTTPException(401, "Invalid or expired session — sign in again.", headers={"WWW-Authenticate": "Bearer"})
    if basic and check_credentials(basic.username, basic.password):
        return basic.username
    raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
