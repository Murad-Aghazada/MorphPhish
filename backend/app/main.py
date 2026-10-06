import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import settings
from .core.logging import configure_logging
from .api import router, public
configure_logging(settings.log_level)
log=logging.getLogger("app")

_IS_PROD=settings.app_env.lower() in ("production","prod")

def _check_secrets():
    # The lab defaults (root/root, change-me) are deliberate for local use. Outside
    # development they are a broken-authentication risk: refuse to boot in production,
    # warn loudly in any other non-development environment (e.g. staging).
    weak=[]
    if settings.admin_password=="root": weak.append("ADMIN_PASSWORD")
    if settings.app_secret_key.startswith("change-me"): weak.append("APP_SECRET_KEY")
    if not weak or settings.app_env.lower()=="development": return
    msg="insecure default(s) still set: "+", ".join(weak)
    if _IS_PROD:
        raise RuntimeError(f"Refusing to start in production — {msg}. Set strong values before deploying.")
    log.warning("SECURITY: APP_ENV=%s but %s — override before any real deployment.",settings.app_env,msg)

_check_secrets()
app=FastAPI(title=settings.app_name,version="1.0.0",description="Authorized, synthetic-data phishing awareness simulation platform.")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.middleware("http")
async def security_headers(request:Request,call_next):
    resp=await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options","nosniff")
    resp.headers.setdefault("X-Frame-Options","DENY")
    resp.headers.setdefault("Referrer-Policy","no-referrer")
    resp.headers.setdefault("Cross-Origin-Opener-Policy","same-origin")
    if _IS_PROD: resp.headers.setdefault("Strict-Transport-Security","max-age=63072000; includeSubDomains")
    return resp

app.include_router(public)
app.include_router(router)
@app.exception_handler(Exception)
async def unhandled(request:Request, exc:Exception):
    log.exception("Unhandled error on %s %s",request.method,request.url.path)
    return JSONResponse(status_code=500,content={"detail":"Internal server error"})
