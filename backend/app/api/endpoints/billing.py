"""
Stripe billing endpoints.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.clinician import Clinician
from app.schemas.billing import CheckoutSessionRequest, CheckoutSessionResponse, PortalResponse
from app.services.billing_service import StripeBillingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

billing_service = StripeBillingService()


@router.post("/setup", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    payload: CheckoutSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Create a Stripe Checkout session for subscription setup."""
    try:
        session = await billing_service.create_checkout_session(
            agency_id=payload.agency_id,
            clinician_email=current_user.email,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
        return session
    except Exception as exc:
        logger.exception("Failed to create checkout session")
        raise HTTPException(status_code=500, detail="Failed to create checkout session") from exc


@router.get("/portal", response_model=PortalResponse)
async def get_portal_url(
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Return a Stripe Customer Portal URL for managing the subscription."""
    from sqlalchemy import select
    from app.models.agency import Agency

    result = await db.execute(
        select(Agency).where(Agency.id == current_user.agency_id)
    )
    agency = result.scalar_one_or_none()
    if agency is None or not agency.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer found for this agency",
        )

    try:
        portal_url = await billing_service.get_portal_url(agency.stripe_customer_id)
        return PortalResponse(url=portal_url)
    except Exception as exc:
        logger.exception("Failed to create portal session")
        raise HTTPException(status_code=500, detail="Failed to create portal session") from exc


@router.post("/webhook", status_code=200)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    Verifies the signature and dispatches to the billing service handler.
    """
    payload = await request.body()

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")

    try:
        result = await billing_service.handle_webhook(
            payload=payload,
            sig_header=stripe_signature,
            db=db,
        )
        return result
    except ValueError as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from exc
    except Exception as exc:
        logger.exception("Stripe webhook handler error")
        raise HTTPException(status_code=500, detail="Webhook processing failed") from exc
