"""Persist immutable Stripe checkout attempts.

Revision ID: a291c0ffee01
Revises: 2c0b2c5551da
"""
import sqlalchemy as sa
from alembic import op

revision = "a291c0ffee01"
down_revision = "2c0b2c5551da"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_checkouts",
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("attempt_key", sa.String(64), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("checkout_url", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("payment_id"),
        sa.UniqueConstraint("attempt_key"),
        sa.UniqueConstraint("session_id"),
    )


def downgrade():
    op.drop_table("payment_checkouts")
