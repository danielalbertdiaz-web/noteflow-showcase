"""
Stripe billing service: checkout sessions, customer portal, webhook handling.
"""

import logging
from typing import Optional
from uuid import UUID

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.billing import CheckoutSessionResponse

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeBillingService:
    """
    Handles all Stripe interactions: subscriptions, customer portal, webhooks.
    """

    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_checkout_session(
        self,
        agency_id: str,
        clinician_email: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> CheckoutSessionResponse:
        """
        Create a Stripe Checkout session for a per-seat subscription.

        Reuses an existing Stripe customer if one exists for the agency.
        """
        import asyncio

        success = success_url or f"{settings.APP_URL}/billing/success"
        cancel = cancel_url or f"{settings.APP_URL}/billing/cancel"

        # Look up existing customer for this agency
        from app.models.agency import Agency
        from app.core.database import AsyncSessionLocal

        stripe_customer_id: Optional[str] = None
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Agency).where(Agency.id == UUID(agency_id)))
            agency = result.scalar_one_or_none()
            if agency:
                stripe_customer_id = agency.stripe_customer_id

        if not stripe_customer_id:
            # Create a new Stripe customer
            loop = asyncio.get_running_loop()
            customer = await loop.run_in_executor(
                None,
                lambda: stripe.Customer.create(
                    email=clinician_email,
                    metadata={"agency_id": agency_id},
                ),
            )
            stripe_customer_id = customer.id

            # Persist the new customer ID
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Agency).where(Agency.id == UUID(agency_id)))
                agency = result.scalar_one_or_none()
                if agency:
                    agency.stripe_customer_id = stripe_customer_id
                    await db.commit()

        loop = asyncio.get_running_loop()
        session = await loop.run_in_executor(
            None,
            lambda: stripe.checkout.Session.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": settings.STRIPE_PRICE_ID,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel,
                metadata={"agency_id": agency_id},
                subscription_data={
                    "metadata": {"agency_id": agency_id},
                },
                allow_promotion_codes=True,
                billing_address_collection="required",
            ),
        )

        return CheckoutSessionResponse(url=session.url, session_id=session.id)

    async def get_portal_url(self, stripe_customer_id: str) -> str:
        """Return a Stripe Billing Portal URL for the customer."""
        import asyncio

        loop = asyncio.get_running_loop()
        portal = await loop.run_in_executor(
            None,
            lambda: stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=f"{settings.APP_URL}/billing",
            ),
        )
        return portal.url

    async def handle_webhook(
        self,
        payload: bytes,
        sig_header: str,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """
        Verify and process a Stripe webhook event.

        Handles: subscription created/updated/deleted, payment_intent failed.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as exc:
            raise ValueError(f"Stripe signature verification failed: {exc}") from exc

        event_type = event["type"]
        event_data = event["data"]["object"]

        logger.info("Processing Stripe webhook: %s (id=%s)", event_type, event["id"])

        if event_type == "customer.subscription.created":
            await self._handle_subscription_created(event_data, db)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(event_data, db)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(event_data, db)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(event_data, db)
        elif event_type == "checkout.session.completed":
            await self._handle_checkout_completed(event_data, db)
        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)

        return {"received": True, "event_id": event["id"]}

    async def add_seat(self, stripe_customer_id: str) -> dict:
        """
        Increment the subscription quantity by 1 (add a seat).
        Returns the updated subscription item.
        """
        import asyncio

        loop = asyncio.get_running_loop()
        subscriptions = await loop.run_in_executor(
            None,
            lambda: stripe.Subscription.list(customer=stripe_customer_id, limit=1),
        )
        if not subscriptions.data:
            raise ValueError(f"No active subscription for customer {stripe_customer_id}")

        subscription = subscriptions.data[0]
        item = subscription["items"]["data"][0]
        current_qty = item.get("quantity", 1)

        updated_item = await loop.run_in_executor(
            None,
            lambda: stripe.SubscriptionItem.modify(
                item["id"],
                quantity=current_qty + 1,
                proration_behavior="always_invoice",
            ),
        )
        return {"subscription_item_id": item["id"], "quantity": updated_item["quantity"]}

    async def remove_seat(self, stripe_customer_id: str, subscription_item_id: str) -> dict:
        """
        Decrement subscription quantity by 1 (remove a seat).
        Will not go below 1.
        """
        import asyncio

        loop = asyncio.get_running_loop()
        item = await loop.run_in_executor(
            None,
            lambda: stripe.SubscriptionItem.retrieve(subscription_item_id),
        )
        current_qty = item.get("quantity", 1)
        new_qty = max(1, current_qty - 1)

        updated_item = await loop.run_in_executor(
            None,
            lambda: stripe.SubscriptionItem.modify(
                subscription_item_id,
                quantity=new_qty,
                proration_behavior="always_invoice",
            ),
        )
        return {"subscription_item_id": subscription_item_id, "quantity": updated_item["quantity"]}

    # ------------------------------------------------------------------
    # Private webhook handlers
    # ------------------------------------------------------------------

    async def _handle_subscription_created(
        self, subscription: dict, db: Optional[AsyncSession]
    ) -> None:
        agency_id = subscription.get("metadata", {}).get("agency_id")
        logger.info("Subscription created for agency %s: %s", agency_id, subscription["id"])
        if db and agency_id:
            from app.models.agency import Agency, AgencyStatus
            result = await db.execute(select(Agency).where(Agency.id == UUID(agency_id)))
            agency = result.scalar_one_or_none()
            if agency:
                agency.status = AgencyStatus.active
                await db.flush()

    async def _handle_subscription_updated(
        self, subscription: dict, db: Optional[AsyncSession]
    ) -> None:
        agency_id = subscription.get("metadata", {}).get("agency_id")
        sub_status = subscription.get("status")
        logger.info(
            "Subscription updated for agency %s: status=%s", agency_id, sub_status
        )
        if db and agency_id:
            from app.models.agency import Agency, AgencyStatus
            result = await db.execute(select(Agency).where(Agency.id == UUID(agency_id)))
            agency = result.scalar_one_or_none()
            if agency:
                agency.status = AgencyStatus.active if sub_status == "active" else AgencyStatus.inactive
                await db.flush()

    async def _handle_subscription_deleted(
        self, subscription: dict, db: Optional[AsyncSession]
    ) -> None:
        agency_id = subscription.get("metadata", {}).get("agency_id")
        logger.info("Subscription cancelled for agency %s", agency_id)
        if db and agency_id:
            from app.models.agency import Agency, AgencyStatus
            result = await db.execute(select(Agency).where(Agency.id == UUID(agency_id)))
            agency = result.scalar_one_or_none()
            if agency:
                agency.status = AgencyStatus.inactive
                await db.flush()

    async def _handle_payment_failed(
        self, invoice: dict, db: Optional[AsyncSession]
    ) -> None:
        customer_id = invoice.get("customer")
        logger.warning("Payment failed for Stripe customer %s", customer_id)
        # Could send a notification email here

    async def _handle_checkout_completed(
        self, session: dict, db: Optional[AsyncSession]
    ) -> None:
        """Persist subscription ID after successful checkout."""
        subscription_id = session.get("subscription")
        agency_id = session.get("metadata", {}).get("agency_id")
        logger.info(
            "Checkout completed for agency %s, subscription %s",
            agency_id, subscription_id,
        )
