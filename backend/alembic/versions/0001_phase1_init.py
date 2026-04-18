"""phase1 init

Revision ID: 0001_phase1_init
Revises:
Create Date: 2026-03-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_phase1_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "guest_profiles",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("occupation", sa.String(), nullable=True),
        sa.Column("background_summary", sa.Text(), nullable=True),
        sa.Column("personality_summary", sa.Text(), nullable=True),
        sa.Column("attachment_style", sa.String(), nullable=True),
        sa.Column("appearance_tags", sa.JSON(), nullable=False),
        sa.Column("personality_tags", sa.JSON(), nullable=False),
        sa.Column("preferred_traits", sa.JSON(), nullable=False),
        sa.Column("disliked_traits", sa.JSON(), nullable=False),
        sa.Column("commitment_goal", sa.String(), nullable=True),
        sa.Column("imported_payload", sa.JSON(), nullable=False),
        sa.Column("soul_data", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "simulation_runs",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_scene_index", sa.Integer(), nullable=False),
        sa.Column("current_scene_code", sa.String(), nullable=True),
        sa.Column("latest_scene_summary", sa.Text(), nullable=True),
        sa.Column("latest_audit_snippet", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("strategy_cards", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scene_runs",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("scene_index", sa.Integer(), nullable=False),
        sa.Column("scene_code", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("claim_token", sa.String(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("director_output", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_run_id", "scene_code"),
    )
    op.create_table(
        "relationship_states",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("protagonist_guest_id", sa.String(), nullable=False),
        sa.Column("target_guest_id", sa.String(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("recent_trend", sa.String(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["protagonist_guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_guest_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_run_id", "protagonist_guest_id", "target_guest_id"),
    )
    op.create_table(
        "state_snapshots",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("log_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("state_snapshots")
    op.drop_table("relationship_states")
    op.drop_table("scene_runs")
    op.drop_table("simulation_runs")
    op.drop_table("guest_profiles")
    op.drop_table("projects")

