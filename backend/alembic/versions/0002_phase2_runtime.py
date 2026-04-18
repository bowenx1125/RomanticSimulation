"""phase2 runtime

Revision ID: 0002_phase2_runtime
Revises: 0001_phase1_init
Create Date: 2026-03-29 14:58:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_phase2_runtime"
down_revision = "0001_phase1_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_messages",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("speaker_guest_id", sa.String(), nullable=False),
        sa.Column("speaker_name", sa.String(), nullable=False),
        sa.Column("message_role", sa.String(), nullable=False),
        sa.Column("utterance", sa.Text(), nullable=False),
        sa.Column("behavior_summary", sa.Text(), nullable=True),
        sa.Column("intent_tags", sa.JSON(), nullable=False),
        sa.Column("target_guest_ids", sa.JSON(), nullable=False),
        sa.Column("visible_context_summary", sa.JSON(), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agent_turns",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("guest_id", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("normalized_output", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_run_id", "turn_index", "guest_id"),
    )
    op.create_table(
        "scene_artifacts",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_run_id", "artifact_type"),
    )


def downgrade() -> None:
    op.drop_table("scene_artifacts")
    op.drop_table("agent_turns")
    op.drop_table("scene_messages")
