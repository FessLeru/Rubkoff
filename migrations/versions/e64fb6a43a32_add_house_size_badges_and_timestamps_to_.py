"""Add house_size, badges, and timestamps to House model

Revision ID: e64fb6a43a32
Revises: 104599769348
Create Date: 2025-06-08 16:10:33.447510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e64fb6a43a32'
down_revision: Union[str, None] = '104599769348'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
