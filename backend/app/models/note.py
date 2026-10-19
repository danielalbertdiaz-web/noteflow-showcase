import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import EncryptedString


class VisitType(str, enum.Enum):
    initial_eval = "initial_eval"
    follow_up = "follow_up"
    discharge = "discharge"
    recert = "recert"


class NoteStatus(str, enum.Enum):
    draft = "draft"
    processing = "processing"
    reviewed = "reviewed"
    approved = "approved"
    submitted = "submitted"
    failed = "failed"


class KinnserEntryStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clinician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clinicians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    patient_name: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    visit_type: Mapped[VisitType] = mapped_column(
        Enum(VisitType, name="visit_type"),
        nullable=False,
    )
    raw_input: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    raw_transcript: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    structured_note: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)  # JSON stored as encrypted string
    status: Mapped[NoteStatus] = mapped_column(
        Enum(NoteStatus, name="note_status"),
        nullable=False,
        default=NoteStatus.draft,
        server_default=NoteStatus.draft.value,
        index=True,
    )
    kinnser_entry_status: Mapped[KinnserEntryStatus | None] = mapped_column(
        Enum(KinnserEntryStatus, name="kinnser_entry_status"),
        nullable=True,
    )
    kinnser_screenshot_url: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
    clinician: Mapped["Clinician"] = relationship("Clinician", back_populates="notes")  # noqa: F821
