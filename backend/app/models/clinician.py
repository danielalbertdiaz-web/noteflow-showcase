import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClinicianRole(str, enum.Enum):
    admin = "admin"
    clinician = "clinician"


class ClinicianStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Clinician(Base):
    __tablename__ = "clinicians"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    kinnser_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kinnser_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[ClinicianRole] = mapped_column(
        Enum(ClinicianRole, name="clinician_role"),
        nullable=False,
        default=ClinicianRole.clinician,
        server_default=ClinicianRole.clinician.value,
    )
    status: Mapped[ClinicianStatus] = mapped_column(
        Enum(ClinicianStatus, name="clinician_status"),
        nullable=False,
        default=ClinicianStatus.active,
        server_default=ClinicianStatus.active.value,
    )
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(tz=timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

    # Relationships
    agency: Mapped["Agency"] = relationship("Agency", back_populates="clinicians")  # noqa: F821
    notes: Mapped[list["Note"]] = relationship(  # noqa: F821
        "Note", back_populates="clinician", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog", back_populates="actor"
    )
