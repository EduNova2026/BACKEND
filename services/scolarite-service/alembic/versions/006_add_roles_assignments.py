from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_roles_assignments"
down_revision = "005_read_optimization_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enseignant_groupes",
        sa.Column("enseignant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("groupe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["groupe_id"], ["groupes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("enseignant_id", "groupe_id"),
    )
    op.create_index(
        "ix_enseignant_groupes_enseignant_id",
        "enseignant_groupes",
        ["enseignant_id"],
    )

    op.create_table(
        "responsable_promotions",
        sa.Column("responsable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("promotion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["promotion_id"], ["promotions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("responsable_id", "promotion_id"),
    )
    op.create_index(
        "ix_responsable_promotions_responsable_id",
        "responsable_promotions",
        ["responsable_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_responsable_promotions_responsable_id",
        table_name="responsable_promotions",
    )
    op.drop_table("responsable_promotions")
    op.drop_index("ix_enseignant_groupes_enseignant_id", table_name="enseignant_groupes")
    op.drop_table("enseignant_groupes")
