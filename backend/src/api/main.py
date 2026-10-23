"""
src/api/main.py
===============
FastAPI application entry point.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.settings import settings
from src.api.logging import setup_logging
from src.api.routes import health, runs, frames, simulate, ws

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="OceanFlow — Ocean Plastic Tracker API", version="1.0.0")


@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(
        f"→ {request.method} {request.url.path}",
        extra={"request_id": request_id, "endpoint": request.url.path}
    )
    
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={"request_id": request_id, "endpoint": request.url.path}
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL", "message": "Internal server error"}},
            headers={"X-Request-ID": request_id}
        )

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", None)
    headers = getattr(exc, "headers", None) or {}
    if request_id:
        headers["X-Request-ID"] = request_id

    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
            headers=headers
        )

    code = "UNKNOWN"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 429:
        code = "TOO_MANY_REQUESTS"
    elif exc.status_code == 422:
        code = "INVALID_PARAMS"
        
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
        headers=headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_PARAMS", "message": str(exc)}},
        headers=headers
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,   prefix="/api", tags=["health"])
app.include_router(runs.router,     prefix="/api", tags=["runs"])
app.include_router(frames.router,   prefix="/api", tags=["frames"])
app.include_router(simulate.router, prefix="/api", tags=["simulate"])
app.include_router(ws.router,       prefix="/api", tags=["ws"])
