import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import EncryptedString


class AgencyStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    trial = "trial"


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    kinnser_username: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    kinnser_password: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    kinnser_totp_secret: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    status: Mapped[AgencyStatus] = mapped_column(
        Enum(AgencyStatus, name="agency_status"),
        nullable=False,
        default=AgencyStatus.trial,
        server_default=AgencyStatus.trial.value,
    )
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
    clinicians: Mapped[list["Clinician"]] = relationship(  # noqa: F821
        "Clinician", back_populates="agency", cascade="all, delete-orphan"
    )
