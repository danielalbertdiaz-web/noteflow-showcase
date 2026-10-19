from typing import Any, Optional

from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    agency_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class PortalResponse(BaseModel):
    url: str


class WebhookEvent(BaseModel):
    """Mirrors Stripe's event structure for documentation purposes."""
    id: str
    type: str
    data: dict[str, Any]
    livemode: bool
