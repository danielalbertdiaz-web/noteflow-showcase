from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.agency import AgencyStatus
from app.models.clinician import ClinicianRole, ClinicianStatus


# ---------------------------------------------------------------------------
# Agency schemas
# ---------------------------------------------------------------------------

class AgencyCreate(BaseModel):
    name: str
    kinnser_username: Optional[str] = None
    kinnser_password: Optional[str] = None
    kinnser_totp_secret: Optional[str] = None


class AgencyResponse(BaseModel):
    id: UUID
    name: str
    status: AgencyStatus
    stripe_customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Clinician schemas
# ---------------------------------------------------------------------------

class ClinicianCreate(BaseModel):
    email: EmailStr
    name: str
    license_number: Optional[str] = None
    role: ClinicianRole = ClinicianRole.clinician


class ClinicianResponse(BaseModel):
    id: UUID
    agency_id: UUID
    email: str
    name: str
    license_number: Optional[str] = None
    role: ClinicianRole
    status: ClinicianStatus
    mfa_enabled: bool
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClinicianList(BaseModel):
    items: list[ClinicianResponse]
    total: int


class KinnserCredentialsUpdate(BaseModel):
    kinnser_username: str
    kinnser_password: str


class KinnserCredentialsResponse(BaseModel):
    kinnser_username: Optional[str] = None
    has_password: bool = False
