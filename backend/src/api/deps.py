"""
src/api/deps.py
===============
FastAPI dependency providers.
"""

from __future__ import annotations

from functools import lru_cache

import redis as redis_lib
from redis import asyncio as aioredis

from src.settings import settings


def get_settings():
    return settings


# ── Sync Redis (used by HTTP routes and Celery task) ──────────────────────────

@lru_cache(maxsize=1)
def _make_redis_client() -> redis_lib.Redis:
    """Singleton sync Redis client — one connection pool shared across all requests."""
    return redis_lib.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis_lib.Redis:
    """FastAPI dependency that returns the shared sync Redis client."""
    return _make_redis_client()


# ── Async Redis (used exclusively by WebSocket handlers) ─────────────────────

@lru_cache(maxsize=1)
def _make_async_redis_client() -> aioredis.Redis:
    """
    Singleton async Redis client — one connection pool for all WS handlers.
    MUST NOT be shared with the sync Celery worker client.
    """
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def get_async_redis() -> aioredis.Redis:
    """Return the shared async Redis client for WebSocket handlers."""
    return _make_async_redis_client()
