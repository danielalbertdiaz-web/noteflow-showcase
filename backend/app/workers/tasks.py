"""
Celery tasks for NoteFlow background processing.

Tasks:
  process_voice_note  – STT transcription + LLM structuring
  process_text_note   – LLM structuring from raw text
  submit_to_kinnser   – Playwright EMR automation
"""

import asyncio
import json
import logging
from uuid import UUID

from celery import Task
from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run a coroutine synchronously inside a Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class BaseTask(Task):
    """Base Celery task with shared retry logic."""

    abstract = True
    max_retries = 3
    default_retry_delay = 60  # seconds


@celery_app.task(bind=True, base=BaseTask, name="app.workers.tasks.process_voice_note")
def process_voice_note(self, note_id: str) -> dict:
    """
    Process a voice note:
      1. Fetch audio from S3
      2. Transcribe via Deepgram (with Whisper fallback)
      3. Structure with Claude
      4. Persist the structured note
    """
    return _run_async(_process_voice_note_async(self, note_id))


@celery_app.task(bind=True, base=BaseTask, name="app.workers.tasks.process_text_note")
def process_text_note(self, note_id: str) -> dict:
    """
    Process a text note:
      1. Load raw_input text from the DB
      2. Structure with Claude
      3. Persist the structured note
    """
    return _run_async(_process_text_note_async(self, note_id))


@celery_app.task(bind=True, base=BaseTask, name="app.workers.tasks.submit_to_kinnser")
def submit_to_kinnser(self, note_id: str) -> dict:
    """
    Submit an approved note to Kinnser EMR:
      1. Load note + agency credentials
      2. Launch Playwright
      3. Login, navigate to patient, enter note fields
      4. Save and capture screenshot
      5. Update note kinnser_entry_status
    """
    return _run_async(_submit_to_kinnser_async(self, note_id))


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------

async def _process_voice_note_async(task: Task, note_id: str) -> dict:
    from app.core.database import get_db_context
    from app.models.note import Note, NoteStatus
    from app.services.stt_service import DeepgramSTTService
    from app.services.llm_service import NoteStructuringService
    from app.services.storage_service import S3StorageService
    from app.services.audit_service import AuditService

    stt = DeepgramSTTService()
    llm = NoteStructuringService()
    storage = S3StorageService()

    async with get_db_context() as db:
        # Load note
        result = await db.execute(select(Note).where(Note.id == UUID(note_id)))
        note = result.scalar_one_or_none()
        if note is None:
            logger.error("Note %s not found", note_id)
            return {"error": "Note not found"}

        try:
            # Stage 1: Fetch audio from S3
            note.status = NoteStatus.processing
            await db.flush()

            s3_key = note.raw_input  # stored as s3:// URL
            if not s3_key:
                raise ValueError("No audio S3 key on note")

            audio_bytes = await storage.get_object(s3_key)
            logger.info("Fetched audio for note %s (%d bytes)", note_id, len(audio_bytes))

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="stt_started",
                resource_type="note",
                resource_id=note.id,
                metadata={"s3_key": s3_key},
            )

            # Stage 2: Transcribe
            transcript = await stt.transcribe_audio(audio_bytes, "audio/wav")
            note.raw_transcript = transcript
            await db.flush()
            logger.info("Transcription complete for note %s (%d chars)", note_id, len(transcript))

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="stt_complete",
                resource_type="note",
                resource_id=note.id,
                metadata={"transcript_length": len(transcript)},
            )

            # Stage 3: Structure with LLM
            result_data = await llm.structure_note(transcript, note.visit_type.value)
            note.structured_note = json.dumps(result_data["structured_note"])
            note.confidence_score = result_data["confidence_score"]
            note.flags = result_data.get("flags")
            note.status = NoteStatus.reviewed
            await db.flush()

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="note_structured",
                resource_type="note",
                resource_id=note.id,
                metadata={
                    "confidence_score": result_data["confidence_score"],
                    "has_flags": bool(result_data.get("flags")),
                },
            )

            logger.info("Voice note %s processed successfully", note_id)
            return {"note_id": note_id, "status": note.status.value}

        except Exception as exc:
            logger.exception("Failed to process voice note %s: %s", note_id, exc)
            note.status = NoteStatus.failed
            note.flags = {"processing_error": str(exc)}
            await db.flush()

            # Retry if within retry limit
            try:
                raise task.retry(exc=exc, countdown=60 * (task.request.retries + 1))
            except task.MaxRetriesExceededError:
                logger.error("Max retries exceeded for voice note %s", note_id)
                return {"note_id": note_id, "status": "failed", "error": str(exc)}


async def _process_text_note_async(task: Task, note_id: str) -> dict:
    from app.core.database import get_db_context
    from app.models.note import Note, NoteStatus
    from app.services.llm_service import NoteStructuringService
    from app.services.audit_service import AuditService

    llm = NoteStructuringService()

    async with get_db_context() as db:
        result = await db.execute(select(Note).where(Note.id == UUID(note_id)))
        note = result.scalar_one_or_none()
        if note is None:
            logger.error("Note %s not found", note_id)
            return {"error": "Note not found"}

        try:
            note.status = NoteStatus.processing
            await db.flush()

            raw_text = note.raw_input
            if not raw_text:
                raise ValueError("Note has no raw_input text")

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="note_structuring_started",
                resource_type="note",
                resource_id=note.id,
                metadata={"visit_type": note.visit_type.value},
            )

            result_data = await llm.structure_note(raw_text, note.visit_type.value)
            note.structured_note = json.dumps(result_data["structured_note"])
            note.confidence_score = result_data["confidence_score"]
            note.flags = result_data.get("flags")
            note.status = NoteStatus.reviewed
            await db.flush()

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="note_structured",
                resource_type="note",
                resource_id=note.id,
                metadata={"confidence_score": result_data["confidence_score"]},
            )

            logger.info("Text note %s processed successfully", note_id)
            return {"note_id": note_id, "status": note.status.value}

        except Exception as exc:
            logger.exception("Failed to process text note %s: %s", note_id, exc)
            note.status = NoteStatus.failed
            note.flags = {"processing_error": str(exc)}
            await db.flush()

            try:
                raise task.retry(exc=exc, countdown=60 * (task.request.retries + 1))
            except task.MaxRetriesExceededError:
                return {"note_id": note_id, "status": "failed", "error": str(exc)}


async def _submit_to_kinnser_async(task: Task, note_id: str) -> dict:
    from app.core.database import get_db_context
    from app.models.note import Note, NoteStatus, KinnserEntryStatus
    from app.models.agency import Agency
    from app.models.clinician import Clinician
    from app.services.kinnser_service import KinnserAutomationService
    from app.services.kinnser_field_mapper import map_soap_to_kinnser_fields
    from app.services.audit_service import AuditService

    kinnser = KinnserAutomationService()

    async with get_db_context() as db:
        # Load note with clinician and agency
        result = await db.execute(select(Note).where(Note.id == UUID(note_id)))
        note = result.scalar_one_or_none()
        if note is None:
            return {"error": "Note not found"}

        clinician_result = await db.execute(
            select(Clinician).where(Clinician.id == note.clinician_id)
        )
        clinician = clinician_result.scalar_one_or_none()
        if clinician is None:
            return {"error": "Clinician not found"}

        agency_result = await db.execute(
            select(Agency).where(Agency.id == clinician.agency_id)
        )
        agency = agency_result.scalar_one_or_none()

        # Determine credentials: prefer clinician-level, fallback to agency
        kinnser_user = clinician.kinnser_username or (agency.kinnser_username if agency else None)
        kinnser_pass = clinician.kinnser_password or (agency.kinnser_password if agency else None)
        totp_secret = agency.kinnser_totp_secret if agency else None

        if not kinnser_user:
            note.kinnser_entry_status = KinnserEntryStatus.failed
            note.flags = {"kinnser_error": "No Kinnser credentials configured"}
            await db.flush()
            return {"error": "Kinnser credentials not configured"}

        try:
            note.kinnser_entry_status = KinnserEntryStatus.in_progress
            await db.flush()

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="kinnser_submission_started",
                resource_type="note",
                resource_id=note.id,
                metadata={},
            )

            # Login to Kinnser
            await kinnser.login(
                username=kinnser_user,
                password=kinnser_pass,
                totp_secret=totp_secret,
            )

            # Navigate to patient
            await kinnser.navigate_to_patient(note.patient_id, note.patient_name)

            # Parse structured note
            structured = {}
            if note.structured_note:
                try:
                    structured = json.loads(note.structured_note)
                except json.JSONDecodeError:
                    structured = {}

            structured["visit_date"] = str(note.visit_date)

            # Map SOAP fields to Kinnser form fields
            mapped_fields = map_soap_to_kinnser_fields(structured)
            structured["_mapped_fields"] = mapped_fields

            # Enter the note
            await kinnser.enter_note(structured, note.visit_type.value)

            # Save and take screenshot
            screenshot_url = await kinnser.save_and_verify()

            note.kinnser_entry_status = KinnserEntryStatus.completed
            note.status = NoteStatus.submitted
            note.kinnser_screenshot_url = screenshot_url
            await db.flush()

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="kinnser_submission_complete",
                resource_type="note",
                resource_id=note.id,
                metadata={"screenshot_url": screenshot_url},
            )

            logger.info("Note %s submitted to Kinnser successfully", note_id)
            return {"note_id": note_id, "status": "submitted", "screenshot_url": screenshot_url}

        except Exception as exc:
            logger.exception("Kinnser submission failed for note %s: %s", note_id, exc)
            note.kinnser_entry_status = KinnserEntryStatus.failed
            note.flags = {**(note.flags or {}), "kinnser_error": str(exc)}
            await db.flush()

            await AuditService.log_action(
                db=db,
                actor_id=note.clinician_id,
                action="kinnser_submission_failed",
                resource_type="note",
                resource_id=note.id,
                metadata={"error": str(exc)},
            )

            try:
                raise task.retry(exc=exc, countdown=120 * (task.request.retries + 1))
            except task.MaxRetriesExceededError:
                return {"note_id": note_id, "status": "failed", "error": str(exc)}

        finally:
            await kinnser.close()
