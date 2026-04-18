"""phase3 participants graph

Revision ID: 0003_phase3_participants_graph
Revises: 0002_phase2_runtime
Create Date: 2026-03-31 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_phase3_participants_graph"
down_revision = "0002_phase2_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'guest_profiles' AND column_name = 'role'
          ) THEN
            ALTER TABLE guest_profiles RENAME COLUMN role TO cast_role;
          END IF;
        END
        $$;
        """
    )

    with op.batch_alter_table("guest_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("editable_personality", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("display_order", sa.Integer(), server_default="0", nullable=False)
        )

    op.execute(
        """
        UPDATE guest_profiles
        SET
          editable_personality = jsonb_build_object(
            'extroversion', 50,
            'initiative', 50,
            'emotional_openness', 50,
            'attachment_style', COALESCE(attachment_style, 'secure'),
            'conflict_style', 'avoid_then_explode',
            'self_esteem_stability', 50,
            'pace_preference', 'gradual_but_clear',
            'commitment_goal', COALESCE(commitment_goal, 'serious_relationship'),
            'preferred_traits', COALESCE(preferred_traits, '[]'::json),
            'disliked_traits', COALESCE(disliked_traits, '[]'::json),
            'boundaries', jsonb_build_object('hard_boundaries', '[]'::json, 'soft_boundaries', '[]'::json),
            'expression_style', jsonb_build_object('communication_style', 'balanced', 'reassurance_need', 'medium')
          ),
          display_order = COALESCE(display_order, 0),
          cast_role = CASE
            WHEN cast_role = 'protagonist' THEN 'main_cast'
            WHEN cast_role = 'guest' THEN 'main_cast'
            ELSE COALESCE(cast_role, 'main_cast')
          END;
        """
    )

    op.execute(
        """
        ALTER TABLE relationship_states
        RENAME COLUMN protagonist_guest_id TO source_participant_id;
        """
    )
    op.execute(
        """
        ALTER TABLE relationship_states
        RENAME COLUMN target_guest_id TO target_participant_id;
        """
    )
    with op.batch_alter_table("relationship_states") as batch_op:
        batch_op.add_column(
            sa.Column("relationship_kind", sa.String(), server_default="social_interest", nullable=False)
        )
        batch_op.add_column(
            sa.Column("last_event_tags", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("updated_by_scene_run_id", sa.String(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_relationship_states_updated_by_scene_run_id",
            "scene_runs",
            ["updated_by_scene_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'relationship_states_simulation_run_id_protagonist_guest_id_target_guest_id_key'
          ) THEN
            ALTER TABLE relationship_states
            DROP CONSTRAINT relationship_states_simulation_run_id_protagonist_guest_id_target_guest_id_key;
          END IF;
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'relationship_states_simulation_run_id_source_participant_id_target_participant_id_key'
          ) THEN
            ALTER TABLE relationship_states
            DROP CONSTRAINT relationship_states_simulation_run_id_source_participant_id_target_participant_id_key;
          END IF;
        END
        $$;
        """
    )
    op.create_unique_constraint(
        "uq_relationship_states_pairwise_graph",
        "relationship_states",
        ["simulation_run_id", "source_participant_id", "target_participant_id", "relationship_kind"],
    )

    op.create_table(
        "personality_presets",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "participant_personality_overrides",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("simulation_run_id", sa.String(), nullable=True),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("preset_slug", sa.String(), nullable=True),
        sa.Column("override_data", sa.JSON(), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "participant_scene_memories",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("target_participant_ids", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("event_tags", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["guest_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scene_event_links",
        sa.Column("simulation_run_id", sa.String(), nullable=False),
        sa.Column("scene_run_id", sa.String(), nullable=False),
        sa.Column("source_participant_id", sa.String(), nullable=True),
        sa.Column("target_participant_ids", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("event_tags", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scene_run_id"], ["scene_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_participant_id"], ["guest_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO personality_presets (id, slug, name, description, values)
        VALUES
          (
            md5(random()::text || clock_timestamp()::text),
            'steady-anchor',
            '稳态支点',
            '更稳定、更耐受冲突，适合多人环境中的低波动角色。',
            jsonb_build_object(
              'extroversion', 48,
              'initiative', 52,
              'emotional_openness', 44,
              'attachment_style', 'secure',
              'conflict_style', 'steady_boundary',
              'self_esteem_stability', 72
            )
          ),
          (
            md5(random()::text || clock_timestamp()::text),
            'spark-chaser',
            '火花追逐者',
            '更外向主动，喜欢推进气氛，但也更容易制造张力。',
            jsonb_build_object(
              'extroversion', 78,
              'initiative', 74,
              'emotional_openness', 68,
              'attachment_style', 'anxious',
              'conflict_style', 'press_then_clarify',
              'self_esteem_stability', 45
            )
          ),
          (
            md5(random()::text || clock_timestamp()::text),
            'careful-observer',
            '谨慎观察者',
            '不抢中心，但会持续收集线索，对被理解感更敏感。',
            jsonb_build_object(
              'extroversion', 34,
              'initiative', 39,
              'emotional_openness', 42,
              'attachment_style', 'avoidant',
              'conflict_style', 'observe_then_withdraw',
              'self_esteem_stability', 58
            )
          )
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("scene_event_links")
    op.drop_table("participant_scene_memories")
    op.drop_table("participant_personality_overrides")
    op.drop_table("personality_presets")
    op.drop_constraint("uq_relationship_states_pairwise_graph", "relationship_states", type_="unique")
    with op.batch_alter_table("relationship_states") as batch_op:
        batch_op.drop_constraint("fk_relationship_states_updated_by_scene_run_id", type_="foreignkey")
        batch_op.drop_column("updated_by_scene_run_id")
        batch_op.drop_column("last_event_tags")
        batch_op.drop_column("relationship_kind")
    op.execute("ALTER TABLE relationship_states RENAME COLUMN target_participant_id TO target_guest_id;")
    op.execute("ALTER TABLE relationship_states RENAME COLUMN source_participant_id TO protagonist_guest_id;")
    op.create_unique_constraint(
        "relationship_states_simulation_run_id_protagonist_guest_id_target_guest_id_key",
        "relationship_states",
        ["simulation_run_id", "protagonist_guest_id", "target_guest_id"],
    )
    with op.batch_alter_table("guest_profiles") as batch_op:
        batch_op.drop_column("display_order")
        batch_op.drop_column("is_active")
        batch_op.drop_column("editable_personality")
    op.execute("ALTER TABLE guest_profiles RENAME COLUMN cast_role TO role;")
