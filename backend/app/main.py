"""
NoteFlow FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings
from app.core.database import engine
from app.api.endpoints import auth, notes, users, billing, health

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentry initialisation (no-op when SENTRY_DSN is unset)
# ---------------------------------------------------------------------------

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment="production" if not settings.APP_URL.startswith("http://localhost") else "development",
        send_default_pii=False,  # HIPAA: never send PII to Sentry
    )
    logger.info("Sentry initialised")


# ---------------------------------------------------------------------------
# Lifespan handler
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("NoteFlow API starting up...")

    # Create tables if they don't exist (production bootstrap)
    from app.core.database import Base
    from app.models import clinician, note, audit_log  # noqa: F401 - ensure models are imported
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))
    logger.info("Database tables created/verified")

    yield

    # Cleanup on shutdown
    logger.info("NoteFlow API shutting down...")
    await engine.dispose()
    logger.info("Database engine disposed")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    redirect_slashes=False,
    title="NoteFlow API",
    description=(
        "HIPAA-compliant PT clinical documentation automation. "
        "Voice-to-structured-SOAP via AI, with Kinnser EMR auto-entry."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(users.router)
app.include_router(billing.router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
async def root():
    return {"service": "NoteFlow API", "version": "1.0.0", "status": "ok"}


@app.post("/seed", tags=["admin"])
async def seed_demo_data():
    """Create demo agency + clinician. Idempotent."""
    import uuid
    from sqlalchemy import select, text
    from app.core.database import AsyncSessionLocal
    from app.models.agency import Agency, AgencyStatus
    from app.models.clinician import Clinician, ClinicianRole, ClinicianStatus

    async with AsyncSessionLocal() as session:
        # Check if demo user exists
        result = await session.execute(
            select(Clinician).where(Clinician.email == "demo@example.org")
        )
        existing = result.scalar_one_or_none()
        if existing:
            return {"message": "Demo data already exists", "email": "demo@example.org", "user_id": str(existing.id)}

        # Create agency
        agency = Agency(
            id=uuid.uuid4(),
            name="Acme Home Health",
            status=AgencyStatus.active,
        )
        session.add(agency)
        await session.flush()

        # Create clinician
        clinician = Clinician(
            id=uuid.uuid4(),
            agency_id=agency.id,
            email="demo@example.org",
            name="Jane Doe",
            role=ClinicianRole.admin,
            status=ClinicianStatus.active,
        )
        session.add(clinician)
        await session.commit()

        return {
            "message": "Demo data created",
            "email": "demo@example.org",
            "user_id": str(clinician.id),
            "agency_id": str(agency.id),
        }
