import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import settings
from .core.logging import configure_logging
from .api import router
configure_logging(settings.log_level)
log=logging.getLogger("app")
app=FastAPI(title=settings.app_name,version="1.0.0",description="Authorized, synthetic-data phishing awareness simulation platform.")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
@app.exception_handler(Exception)
async def unhandled(request:Request, exc:Exception):
    log.exception("Unhandled error on %s %s",request.method,request.url.path)
    return JSONResponse(status_code=500,content={"detail":"Internal server error"})
