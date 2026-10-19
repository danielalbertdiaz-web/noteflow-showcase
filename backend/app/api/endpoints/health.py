"""
Health check endpoints.
"""

import logging

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

KINNSER_URL = "https://www.kinnser.net"


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic liveness / readiness check.
    Pings the database and Redis; returns 200 if both are reachable.
    """
    status_map = {"status": "ok", "db": "unknown", "redis": "unknown"}

    # DB ping
    try:
        await db.execute(text("SELECT 1"))
        status_map["db"] = "ok"
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        status_map["db"] = "error"
        status_map["status"] = "degraded"

    # Redis ping
    try:
        async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
            await r.ping()
        status_map["redis"] = "ok"
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)
        status_map["redis"] = "error"
        status_map["status"] = "degraded"

    return status_map


@router.get("/kinnser")
async def kinnser_health():
    """
    Check whether Kinnser's login page is reachable.
    Returns 200 with { "reachable": true/false }.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(KINNSER_URL)
        reachable = response.status_code < 500
    except Exception as exc:
        logger.warning("Kinnser reachability check failed: %s", exc)
        reachable = False

    return {"kinnser_url": KINNSER_URL, "reachable": reachable}
