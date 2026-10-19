from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.note import KinnserEntryStatus, NoteStatus, VisitType


# ---------------------------------------------------------------------------
# Nested SOAP structures
# ---------------------------------------------------------------------------

class VitalSigns(BaseModel):
    blood_pressure: Optional[str] = None          # e.g. "120/80"
    heart_rate: Optional[int] = None              # bpm
    respiratory_rate: Optional[int] = None        # breaths/min
    oxygen_saturation: Optional[float] = None     # %
    temperature: Optional[float] = None           # °F
    weight: Optional[float] = None                # lbs
    height: Optional[float] = None                # inches


class ROMMeasurement(BaseModel):
    joint: str
    movement: str
    active_rom: Optional[float] = None            # degrees
    passive_rom: Optional[float] = None           # degrees
    normal_rom: Optional[float] = None            # degrees for reference


class StrengthTest(BaseModel):
    muscle_group: str
    grade: float = Field(..., ge=0, le=5)         # MMT 0-5
    notes: Optional[str] = None


class FunctionalAssessment(BaseModel):
    activity: str
    score: Optional[float] = None
    scale: Optional[str] = None                   # e.g. "FIM", "Barthel"
    notes: Optional[str] = None


class Subjective(BaseModel):
    chief_complaint: Optional[str] = None
    pain_scale: Optional[float] = Field(None, ge=0, le=10)
    pain_location: Optional[str] = None
    pain_quality: Optional[str] = None
    aggravating_factors: Optional[list[str]] = None
    relieving_factors: Optional[list[str]] = None
    patient_goals: Optional[list[str]] = None
    progress_since_last_visit: Optional[str] = None
    patient_reported_function: Optional[str] = None


class Objective(BaseModel):
    vital_signs: Optional[VitalSigns] = None
    rom_measurements: Optional[list[ROMMeasurement]] = None
    strength_tests: Optional[list[StrengthTest]] = None
    functional_assessments: Optional[list[FunctionalAssessment]] = None
    observation: Optional[str] = None             # general physical findings
    palpation: Optional[str] = None
    special_tests: Optional[dict[str, Any]] = None


class Assessment(BaseModel):
    clinical_impression: Optional[str] = None
    progress_toward_goals: Optional[str] = None
    skilled_care_rationale: Optional[str] = None
    barriers_to_progress: Optional[list[str]] = None
    rehab_potential: Optional[str] = None         # good / fair / poor / guarded
    diagnosis_codes: Optional[list[str]] = None   # ICD-10


class PlanGoal(BaseModel):
    goal: str
    timeframe: Optional[str] = None               # e.g. "4 weeks"
    measurable_outcome: Optional[str] = None


class Plan(BaseModel):
    interventions: Optional[list[str]] = None
    home_exercise_program: Optional[list[str]] = None
    frequency: Optional[str] = None               # e.g. "3x/week"
    duration: Optional[str] = None                # e.g. "6 weeks"
    short_term_goals: Optional[list[PlanGoal]] = None
    long_term_goals: Optional[list[PlanGoal]] = None
    patient_education: Optional[list[str]] = None
    referrals: Optional[list[str]] = None
    next_visit_date: Optional[date] = None


class OASISFields(BaseModel):
    """Subset of OASIS-E fields commonly documented in home health PT notes."""
    m1800_grooming: Optional[int] = Field(None, ge=0, le=3)
    m1810_dress_upper: Optional[int] = Field(None, ge=0, le=3)
    m1820_dress_lower: Optional[int] = Field(None, ge=0, le=3)
    m1830_bathing: Optional[int] = Field(None, ge=0, le=6)
    m1840_toilet_transferring: Optional[int] = Field(None, ge=0, le=5)
    m1850_transferring: Optional[int] = Field(None, ge=0, le=6)
    m1860_ambulation: Optional[int] = Field(None, ge=0, le=6)
    m2020_management_oral_medications: Optional[int] = Field(None, ge=0, le=3)
    fall_risk_score: Optional[float] = None


class SOAPNote(BaseModel):
    subjective: Optional[Subjective] = None
    objective: Optional[Objective] = None
    assessment: Optional[Assessment] = None
    plan: Optional[Plan] = None
    oasis: Optional[OASISFields] = None
    visit_minutes: Optional[int] = None
    travel_minutes: Optional[int] = None
    co_treatment: Optional[bool] = None
    supervision_percent: Optional[float] = Field(None, ge=0, le=100)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    patient_id: str
    patient_name: str
    visit_date: date
    visit_type: VisitType
    raw_input: Optional[str] = None


class NoteUpdate(BaseModel):
    """Partial update of structured note fields. All fields optional."""
    structured_note: Optional[SOAPNote] = None
    patient_name: Optional[str] = None
    visit_date: Optional[date] = None
    visit_type: Optional[VisitType] = None
    status: Optional[NoteStatus] = None


class NoteResponse(BaseModel):
    id: UUID
    clinician_id: UUID
    patient_id: str
    patient_name: str
    visit_date: date
    visit_type: VisitType
    raw_transcript: Optional[str] = None
    structured_note: Optional[SOAPNote] = None
    status: NoteStatus
    kinnser_entry_status: Optional[KinnserEntryStatus] = None
    kinnser_screenshot_url: Optional[str] = None
    confidence_score: Optional[float] = None
    flags: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_structured_note(cls, values: Any) -> Any:
        """
        The DB stores structured_note as an encrypted JSON string.
        Deserialize it so Pydantic can validate the nested SOAPNote.
        We must NOT mutate the ORM object to avoid SQLAlchemy dirty tracking.
        """
        if hasattr(values, "__dict__") and not isinstance(values, dict):
            # SQLAlchemy model instance — convert to dict to avoid mutating ORM
            data = {}
            for col in ['id', 'clinician_id', 'patient_id', 'patient_name',
                        'visit_date', 'visit_type', 'raw_transcript',
                        'structured_note', 'status', 'kinnser_entry_status',
                        'kinnser_screenshot_url', 'confidence_score', 'flags',
                        'created_at', 'updated_at']:
                data[col] = getattr(values, col, None)
            sn = data.get("structured_note")
            if isinstance(sn, str):
                try:
                    data["structured_note"] = json.loads(sn)
                except (json.JSONDecodeError, TypeError):
                    pass
            return data
        elif isinstance(values, dict):
            sn = values.get("structured_note")
            if isinstance(sn, str):
                try:
                    values["structured_note"] = json.loads(sn)
                except (json.JSONDecodeError, TypeError):
                    pass
        return values


class NoteListResponse(BaseModel):
    notes: list[NoteResponse]
    total: int
    page: int
    pageSize: int


class NoteIdResponse(BaseModel):
    note_id: UUID
    status: NoteStatus
