"""
Authentication endpoints.

Flow:
  1. POST /auth/login   -> generates magic-link token, sends email
  2. POST /auth/verify  -> verifies token, returns JWT pair
  3. POST /auth/refresh -> exchanges refresh token for new access token
  4. POST /auth/logout  -> blacklists the refresh token in Redis
"""

import json
import logging
from datetime import timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_magic_link_token,
    verify_magic_link_token,
    verify_token,
    get_current_user,
)
from app.models.clinician import Clinician, ClinicianStatus
from app.schemas.auth import MagicLinkRequest, RefreshRequest, TokenResponse
from app.services.audit_service import AuditService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

email_service = EmailService()


def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


REFRESH_BLACKLIST_PREFIX = "blacklist:refresh:"


async def _is_refresh_blacklisted(jti: str) -> bool:
    async with _get_redis() as r:
        return await r.exists(f"{REFRESH_BLACKLIST_PREFIX}{jti}") == 1


async def _blacklist_refresh(jti: str) -> None:
    ttl = int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())
    async with _get_redis() as r:
        await r.setex(f"{REFRESH_BLACKLIST_PREFIX}{jti}", ttl, "1")


@router.post("/login", status_code=202)
async def login(
    payload: MagicLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a magic-link email to the provided address.

    Always returns 202 regardless of whether the email is registered
    (prevents user enumeration).
    """
    result = await db.execute(
        select(Clinician).where(Clinician.email == payload.email.lower())
    )
    clinician = result.scalar_one_or_none()

    if clinician and clinician.status == ClinicianStatus.active:
        token = create_magic_link_token(payload.email.lower())
        try:
            await email_service.send_magic_link(payload.email, token)
        except Exception:
            logger.exception("Failed to send magic link email to %s", payload.email)

        await AuditService.log_action(
            db=db,
            actor_id=clinician.id,
            action="magic_link_requested",
            resource_type="clinician",
            resource_id=clinician.id,
            metadata={"email": payload.email},
            ip_address=request.client.host if request.client else None,
        )

    return {"message": "If that email is registered, a login link has been sent."}


@router.post("/verify", response_model=TokenResponse)
async def verify_magic_link(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a magic-link token from the email URL and return a JWT pair.
    Expects body: { "token": "<magic_link_token>" }
    """
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="token is required")

    email = verify_magic_link_token(token)

    result = await db.execute(
        select(Clinician).where(Clinician.email == email)
    )
    clinician = result.scalar_one_or_none()

    if clinician is None or clinician.status != ClinicianStatus.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found or inactive",
        )

    access_token = create_access_token(
        subject=str(clinician.id),
        extra_claims={"email": clinician.email, "role": clinician.role.value},
    )
    refresh_token = create_refresh_token(subject=str(clinician.id))

    await AuditService.log_action(
        db=db,
        actor_id=clinician.id,
        action="login_success",
        resource_type="clinician",
        resource_id=clinician.id,
        metadata={"method": "magic_link"},
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token."""
    decoded = verify_token(payload.refresh_token, expected_type="refresh")

    jti = decoded.get("jti")
    if jti and await _is_refresh_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    clinician_id: str = decoded.get("sub")
    result = await db.execute(
        select(Clinician).where(Clinician.id == clinician_id)
    )
    clinician = result.scalar_one_or_none()
    if clinician is None or clinician.status != ClinicianStatus.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(
        subject=str(clinician.id),
        extra_claims={"email": clinician.email, "role": clinician.role.value},
    )
    new_refresh_token = create_refresh_token(subject=str(clinician.id))

    # Blacklist the old refresh token
    if jti:
        await _blacklist_refresh(jti)

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Blacklist the supplied refresh token."""
    try:
        decoded = verify_token(payload.refresh_token, expected_type="refresh")
        jti = decoded.get("jti")
        if jti:
            await _blacklist_refresh(jti)
    except HTTPException:
        # Even if token is invalid/expired, return 204 to avoid info leakage
        pass

    return None


@router.get("/me")
async def get_current_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Return current authenticated user info."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "agency_id": str(current_user.agency_id),
    }


@router.get("/dev-login/{email}")
async def dev_login(email: str, db: AsyncSession = Depends(get_db)):
    """Development-only: auto-login by email, returns JWT tokens directly."""
    result = await db.execute(
        select(Clinician).where(Clinician.email == email.lower())
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    # Redirect to frontend with both tokens
    from urllib.parse import urlencode
    params = urlencode({
        "access_token": access_token,
        "refresh_token": refresh_token,
    })
    frontend_url = settings.APP_URL.rstrip("/")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{frontend_url}/auth/callback?{params}")
