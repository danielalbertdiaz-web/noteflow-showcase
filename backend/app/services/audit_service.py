"""
Audit logging service — records all significant actions for HIPAA compliance.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """
    Creates immutable audit log entries for clinician actions on PHI.

    All methods are static / class methods so this service requires no
    instantiation and can be called from any context.
    """

    @staticmethod
    async def log_action(
        db: AsyncSession,
        actor_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Create and persist an :class:`AuditLog` entry.

        Parameters
        ----------
        db:
            Active async DB session. The caller is responsible for commit.
        actor_id:
            UUID of the Clinician performing the action. May be None for
            system-generated events.
        action:
            Short snake_case action name (e.g. "note_approved").
        resource_type:
            The type of resource being acted upon (e.g. "note", "clinician").
        resource_id:
            UUID of the specific resource instance.
        metadata:
            Arbitrary additional context (e.g. field names, old/new values).
        ip_address:
            Client IP address from the HTTP request.

        Returns
        -------
        AuditLog
            The persisted (but not committed) audit log entry.
        """
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
            ip_address=ip_address,
        )
        db.add(entry)

        try:
            await db.flush()
        except Exception as exc:
            # Audit logging must not crash the main request
            logger.error(
                "Failed to persist audit log [action=%s, actor=%s]: %s",
                action, actor_id, exc,
            )

        return entry
