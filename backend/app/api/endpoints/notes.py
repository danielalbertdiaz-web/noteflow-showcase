"""
Notes endpoints: voice upload, text input, CRUD, approval, Kinnser status.
"""

import json
import logging
from datetime import date
from typing import Optional
from uuid import UUID

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.clinician import Clinician
from app.models.note import Note, NoteStatus, VisitType
from app.schemas.note import (
    NoteCreate,
    NoteIdResponse,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
)
from app.core.config import settings
from app.services.audit_service import AuditService
from app.services.storage_service import S3StorageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notes", tags=["notes"], redirect_slashes=False)

storage = S3StorageService()


def _has_celery() -> bool:
    """Check if Redis/Celery is available."""
    try:
        if not settings.REDIS_URL:
            return False
        import redis as _redis
        r = _redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


@router.post("/voice", response_model=NoteIdResponse, status_code=202)
async def upload_voice_note(
    audio: UploadFile = File(...),
    patient_id: str = Form(...),
    patient_name: str = Form(...),
    visit_date: date = Form(...),
    visit_type: VisitType = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """
    Accept an audio file upload, store in S3, create a draft note,
    and queue the voice processing task.
    """
    from app.workers.tasks import process_voice_note  # late import avoids circular

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    # Create the note record first so we have an ID for S3 key
    note = Note(
        clinician_id=current_user.id,
        patient_id=patient_id,
        patient_name=patient_name,
        visit_date=visit_date,
        visit_type=visit_type,
        status=NoteStatus.processing,
    )
    db.add(note)
    await db.flush()  # get note.id before S3 upload

    # Upload audio to S3
    s3_url = await storage.upload_audio(audio_bytes, str(note.id))
    note.raw_input = s3_url  # store S3 URL as raw_input for workers to fetch
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="note_voice_created",
        resource_type="note",
        resource_id=note.id,
        metadata={"patient_id": patient_id, "visit_type": visit_type},
        ip_address=request.client.host if request and request.client else None,
    )

    # Queue async processing
    process_voice_note.delay(str(note.id))

    return NoteIdResponse(note_id=note.id, status=note.status)


@router.post("/text", response_model=NoteIdResponse, status_code=202)
async def create_text_note(
    payload: NoteCreate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """
    Accept a text/dictation input, create a draft note, queue LLM structuring.
    """
    from app.workers.tasks import process_text_note  # late import

    if not payload.raw_input:
        raise HTTPException(status_code=400, detail="raw_input is required for text notes")

    note = Note(
        clinician_id=current_user.id,
        patient_id=payload.patient_id,
        patient_name=payload.patient_name,
        visit_date=payload.visit_date,
        visit_type=payload.visit_type,
        raw_input=payload.raw_input,
        status=NoteStatus.processing,
    )
    db.add(note)
    await db.flush()
    await db.commit()

    try:
        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            action="note_text_created",
            resource_type="note",
            resource_id=note.id,
            metadata={"patient_id": payload.patient_id},
            ip_address=request.client.host if request and request.client else None,
        )
    except Exception as e:
        logger.warning("Audit logging failed: %s", e)

    if _has_celery():
        process_text_note.delay(str(note.id))
    else:
        # Synchronous fallback when no Redis/Celery
        try:
            from app.services.llm_service import NoteStructuringService
            llm = NoteStructuringService()
            result = await llm.structure_note(note.raw_input, note.visit_type.value if note.visit_type else "follow_up")
            note.structured_note = json.dumps(result["structured_note"])
            note.status = NoteStatus.reviewed
            note.flags = json.dumps({"confidence": result["confidence_score"], "flags": result.get("flags")})
            logger.info("Note %s processed synchronously (no Celery)", note.id)
        except Exception as e:
            logger.error("Sync note processing failed: %s", e)
            # Leave note in processing state if LLM fails - can be retried later
            note.flags = json.dumps({"processing_error": str(e)})
        
        await db.flush()
        await db.commit()

    return NoteIdResponse(note_id=note.id, status=note.status)


@router.get("")
@router.get("/", include_in_schema=False)
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[NoteStatus] = Query(None, alias="status"),
    visit_date_from: Optional[date] = Query(None),
    visit_date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """List the current clinician's notes with optional filters."""
    query = select(Note).where(Note.clinician_id == current_user.id)

    if status_filter is not None:
        query = query.where(Note.status == status_filter)
    if visit_date_from is not None:
        query = query.where(Note.visit_date >= visit_date_from)
    if visit_date_to is not None:
        query = query.where(Note.visit_date <= visit_date_to)

    # Total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    # Paginated results
    query = (
        query.order_by(Note.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    notes = result.scalars().all()

    # Temporarily simplify response to debug schema issues
    note_dicts = []
    for n in notes:
        try:
            note_dict = {
                'id': str(n.id),
                'clinician_id': str(n.clinician_id),
                'patient_id': n.patient_id,
                'patient_name': n.patient_name,
                'visit_date': n.visit_date.isoformat(),
                'visit_type': n.visit_type.value,
                'status': n.status.value,
                'created_at': n.created_at.isoformat(),
                'updated_at': n.updated_at.isoformat(),
                # Optional fields
                'raw_transcript': getattr(n, 'raw_transcript', None),
                'structured_note': getattr(n, 'structured_note', None),
                'confidence_score': getattr(n, 'confidence_score', None),
                'flags': getattr(n, 'flags', None),
                'kinnser_entry_status': getattr(n, 'kinnser_entry_status', None),
                'kinnser_screenshot_url': getattr(n, 'kinnser_screenshot_url', None),
            }
            note_dicts.append(note_dict)
        except Exception as e:
            logger.error("Failed to serialize note %s: %s", n.id, e)
    
    return {
        'notes': note_dicts,
        'total': total,
        'page': page,
        'pageSize': page_size,
    }


@router.get("/stats/dashboard")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Dashboard summary stats for the current clinician."""
    from datetime import date as date_type
    base = select(func.count()).where(Note.clinician_id == current_user.id)

    total_result = await db.execute(base)
    total = total_result.scalar_one()

    pending_result = await db.execute(
        base.where(Note.status.in_([NoteStatus.draft, NoteStatus.reviewed]))
    )
    pending = pending_result.scalar_one()

    processing_result = await db.execute(
        base.where(Note.status == NoteStatus.processing)
    )
    processing = processing_result.scalar_one()

    today = date_type.today()
    submitted_result = await db.execute(
        base.where(Note.status == NoteStatus.approved, Note.visit_date == today)
    )
    submitted_today = submitted_result.scalar_one()

    return {
        "totalNotes": total,
        "pendingReview": pending,
        "submittedToday": submitted_today,
        "processingNotes": processing,
    }


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Get a single note. Clinicians can only access their own notes."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: UUID,
    payload: NoteUpdate,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Update structured note fields or status."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.structured_note is not None:
        note.structured_note = json.dumps(payload.structured_note.model_dump(mode="json"))
    if payload.patient_name is not None:
        note.patient_name = payload.patient_name
    if payload.visit_date is not None:
        note.visit_date = payload.visit_date
    if payload.visit_type is not None:
        note.visit_type = payload.visit_type
    if payload.status is not None:
        note.status = payload.status

    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="note_updated",
        resource_type="note",
        resource_id=note.id,
        metadata={"fields_updated": list(payload.model_fields_set)},
        ip_address=request.client.host if request and request.client else None,
    )

    return NoteResponse.model_validate(note)


@router.patch("/{note_id}/soap", response_model=NoteResponse)
async def update_soap_note(
    note_id: UUID,
    soap_data: dict,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Update just the SOAP structured_note portion of a note."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    # Extract structured_note from the request body
    structured_note = soap_data.get("structured_note")
    if structured_note is not None:
        note.structured_note = json.dumps(structured_note)
        await db.flush()

        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            action="soap_note_updated",
            resource_type="note",
            resource_id=note.id,
            metadata={},
            ip_address=request.client.host if request and request.client else None,
        )

    return NoteResponse.model_validate(note)


@router.post("/{note_id}/approve", response_model=NoteResponse)
async def approve_note(
    note_id: UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """
    Approve a reviewed note and queue it for Kinnser entry.
    Only notes in 'reviewed' status may be approved.
    """
    from app.workers.tasks import submit_to_kinnser  # late import

    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status not in (NoteStatus.reviewed, NoteStatus.draft):
        raise HTTPException(
            status_code=400,
            detail=f"Note must be in 'reviewed' or 'draft' status to approve; current status: {note.status}",
        )

    from app.models.note import KinnserEntryStatus
    note.status = NoteStatus.approved
    note.kinnser_entry_status = KinnserEntryStatus.pending
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="note_approved",
        resource_type="note",
        resource_id=note.id,
        metadata={},
        ip_address=request.client.host if request and request.client else None,
    )

    submit_to_kinnser.delay(str(note.id))

    return NoteResponse.model_validate(note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Delete a note. Only draft or error status notes can be deleted."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status not in (NoteStatus.draft, NoteStatus.error):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete note with status: {note.status}. Only draft or error notes can be deleted.",
        )

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="note_deleted",
        resource_type="note",
        resource_id=note.id,
        metadata={"note_status": note.status},
        ip_address=request.client.host if request and request.client else None,
    )

    await db.delete(note)
    await db.commit()

    return None


@router.post("/{note_id}/submit", response_model=NoteResponse)
async def submit_to_kinnser_endpoint(
    note_id: UUID,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """
    Submit an approved note to Kinnser EMR.
    This endpoint manually triggers Kinnser submission.
    """
    from app.workers.tasks import submit_to_kinnser  # late import

    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status != NoteStatus.approved:
        raise HTTPException(
            status_code=400,
            detail=f"Note must be approved before submission; current status: {note.status}",
        )

    from app.models.note import KinnserEntryStatus
    note.kinnser_entry_status = KinnserEntryStatus.pending
    await db.flush()

    await AuditService.log_action(
        db=db,
        actor_id=current_user.id,
        action="note_submit_requested",
        resource_type="note",
        resource_id=note.id,
        metadata={},
        ip_address=request.client.host if request and request.client else None,
    )

    submit_to_kinnser.delay(str(note.id))

    return NoteResponse.model_validate(note)


@router.get("/{note_id}/status")
async def get_note_kinnser_status(
    note_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Clinician = Depends(get_current_user),
):
    """Get Kinnser entry status for an approved note."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.clinician_id == current_user.id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    return {
        "note_id": str(note.id),
        "note_status": note.status,
        "kinnser_entry_status": note.kinnser_entry_status,
        "kinnser_screenshot_url": note.kinnser_screenshot_url,
    }
