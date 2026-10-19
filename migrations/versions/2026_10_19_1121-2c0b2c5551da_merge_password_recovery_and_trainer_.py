"""merge password recovery and trainer photo migrations

Revision ID: 2c0b2c5551da
Revises: d735a190bc02, 4f0bef929739
Create Date: 2026-10-19 11:21:05.558121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c0b2c5551da'
down_revision: Union[str, Sequence[str], None] = ('d735a190bc02', '4f0bef929739')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
