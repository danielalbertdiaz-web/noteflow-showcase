"""
Agency and clinician management endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.agency import Agency
from app.models.clinician import Clinician, ClinicianRole, ClinicianStatus
from app.schemas.user import (
    AgencyCreate,
    AgencyResponse,
    ClinicianCreate,
    ClinicianList,
    ClinicianResponse,
    KinnserCredentialsResponse,
    KinnserCredentialsUpdate,
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(current_user: Clinician) -> Clinician:
    if current_user.role != ClinicianRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


@router.post("/agencies", response_model=AgencyResponse, status_code=201)
async def create_agency(
    payload: AgencyCreate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Create a new agency. Requires admin role."""
    _require_admin(current_user)

    agency = Agency(
        name=payload.name,
        kinnser_username=payload.kinnser_username,
        kinnser_password=payload.kinnser_password,
        kinnser_totp_secret=payload.kinnser_totp_secret,
    )
    db.add(agency)
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="agency_created",
        resource_type="agency",
        resource_id=agency.id,
        metadata={"name": payload.name},
        ip_address=request.client.host if request and request.client else None,
    )

    return AgencyResponse.model_validate(agency)


@router.post("/agencies/{agency_id}/clinicians", response_model=ClinicianResponse, status_code=201)
async def add_clinician(
    agency_id: UUID,
    payload: ClinicianCreate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Add a clinician to an agency. Admin only."""
    _require_admin(current_user)

    # Verify agency exists and admin belongs to it
    agency_result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = agency_result.scalar_one_or_none()
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found")

    if current_user.agency_id != agency_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add clinicians to a different agency",
        )

    # Check email uniqueness
    existing = await db.execute(
        select(Clinician).where(Clinician.email == payload.email.lower())
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    clinician = Clinician(
        agency_id=agency_id,
        email=payload.email.lower(),
        name=payload.name,
        license_number=payload.license_number,
        role=payload.role,
        status=ClinicianStatus.active,
    )
    db.add(clinician)
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="clinician_added",
        resource_type="clinician",
        resource_id=clinician.id,
        metadata={"email": payload.email, "agency_id": str(agency_id)},
        ip_address=request.client.host if request and request.client else None,
    )

    return ClinicianResponse.model_validate(clinician)


@router.get("/agencies/{agency_id}/clinicians", response_model=ClinicianList)
async def list_clinicians(
    agency_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """List all clinicians in an agency."""
    _require_admin(current_user)

    if current_user.agency_id != agency_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this agency is not allowed",
        )

    count_result = await db.execute(
        select(func.count(Clinician.id)).where(Clinician.agency_id == agency_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Clinician)
        .where(Clinician.agency_id == agency_id)
        .order_by(Clinician.created_at.asc())
    )
    clinicians = result.scalars().all()

    return ClinicianList(
        items=[ClinicianResponse.model_validate(c) for c in clinicians],
        total=total,
    )


@router.delete("/agencies/{agency_id}/clinicians/{clinician_id}", status_code=204)
async def remove_clinician(
    agency_id: UUID,
    clinician_id: UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Deactivate a clinician. Admin only. Cannot remove yourself."""
    _require_admin(current_user)

    if current_user.agency_id != agency_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this agency is not allowed",
        )

    if current_user.id == clinician_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    result = await db.execute(
        select(Clinician).where(
            Clinician.id == clinician_id,
            Clinician.agency_id == agency_id,
        )
    )
    clinician = result.scalar_one_or_none()
    if clinician is None:
        raise HTTPException(status_code=404, detail="Clinician not found")

    clinician.status = ClinicianStatus.inactive
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="clinician_removed",
        resource_type="clinician",
        resource_id=clinician.id,
        metadata={"agency_id": str(agency_id)},
        ip_address=request.client.host if request and request.client else None,
    )

    return None


@router.put("/me/kinnser-credentials")
async def save_kinnser_credentials(
    payload: KinnserCredentialsUpdate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Save the current clinician's personal WellSky/Kinnser credentials."""
    current_user.kinnser_username = payload.kinnser_username
    current_user.kinnser_password = payload.kinnser_password
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="kinnser_credentials_updated",
        resource_type="clinician",
        resource_id=current_user.id,
        metadata={"kinnser_username": payload.kinnser_username},
        ip_address=request.client.host if request and request.client else None,
    )

    return {"message": "Kinnser credentials saved"}


@router.get("/me/kinnser-credentials", response_model=KinnserCredentialsResponse)
async def get_kinnser_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Return whether the current clinician has Kinnser credentials configured."""
    return KinnserCredentialsResponse(
        kinnser_username=current_user.kinnser_username,
        has_password=bool(current_user.kinnser_password),
    )
