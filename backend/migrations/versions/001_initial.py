"""Initial schema: agencies, clinicians, notes, audit_logs

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # ENUM types
    # ------------------------------------------------------------------
    agency_status = postgresql.ENUM(
        "active", "inactive", "trial", name="agency_status", create_type=False
    )
    agency_status.create(op.get_bind(), checkfirst=True)

    clinician_role = postgresql.ENUM(
        "admin", "clinician", name="clinician_role", create_type=False
    )
    clinician_role.create(op.get_bind(), checkfirst=True)

    clinician_status = postgresql.ENUM(
        "active", "inactive", name="clinician_status", create_type=False
    )
    clinician_status.create(op.get_bind(), checkfirst=True)

    visit_type_enum = postgresql.ENUM(
        "initial_eval", "follow_up", "discharge", "recert",
        name="visit_type", create_type=False
    )
    visit_type_enum.create(op.get_bind(), checkfirst=True)

    note_status_enum = postgresql.ENUM(
        "draft", "processing", "reviewed", "approved", "submitted", "failed",
        name="note_status", create_type=False
    )
    note_status_enum.create(op.get_bind(), checkfirst=True)

    kinnser_entry_status_enum = postgresql.ENUM(
        "pending", "in_progress", "completed", "failed",
        name="kinnser_entry_status", create_type=False
    )
    kinnser_entry_status_enum.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # agencies
    # ------------------------------------------------------------------
    op.create_table(
        "agencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("kinnser_username", sa.Text(), nullable=True),
        sa.Column("kinnser_password", sa.Text(), nullable=True),
        sa.Column("kinnser_totp_secret", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "trial", name="agency_status"),
            nullable=False,
            server_default="trial",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agencies_stripe_customer_id", "agencies", ["stripe_customer_id"])

    # ------------------------------------------------------------------
    # clinicians
    # ------------------------------------------------------------------
    op.create_table(
        "clinicians",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "clinician", name="clinician_role"),
            nullable=False,
            server_default="clinician",
        ),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="clinician_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id"],
            ["agencies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_clinicians_email"),
    )
    op.create_index("ix_clinicians_agency_id", "clinicians", ["agency_id"])
    op.create_index("ix_clinicians_email", "clinicians", ["email"], unique=True)
    op.create_index(
        "ix_clinicians_stripe_subscription_id",
        "clinicians",
        ["stripe_subscription_id"],
    )

    # ------------------------------------------------------------------
    # notes
    # ------------------------------------------------------------------
    op.create_table(
        "notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.String(100), nullable=False),
        sa.Column("patient_name", sa.Text(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column(
            "visit_type",
            sa.Enum("initial_eval", "follow_up", "discharge", "recert", name="visit_type"),
            nullable=False,
        ),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("raw_transcript", sa.Text(), nullable=True),
        sa.Column("structured_note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "processing", "reviewed", "approved", "submitted", "failed",
                name="note_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "kinnser_entry_status",
            sa.Enum(
                "pending", "in_progress", "completed", "failed",
                name="kinnser_entry_status",
            ),
            nullable=True,
        ),
        sa.Column("kinnser_screenshot_url", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["clinicians.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_clinician_id", "notes", ["clinician_id"])
    op.create_index("ix_notes_patient_id", "notes", ["patient_id"])
    op.create_index("ix_notes_status", "notes", ["status"])
    op.create_index("ix_notes_visit_date", "notes", ["visit_date"])

    # ------------------------------------------------------------------
    # audit_logs
    # ------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["clinicians.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("notes")
    op.drop_table("clinicians")
    op.drop_table("agencies")

    # Drop ENUM types
    sa.Enum(name="kinnser_entry_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="note_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="visit_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="clinician_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="clinician_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agency_status").drop(op.get_bind(), checkfirst=True)
