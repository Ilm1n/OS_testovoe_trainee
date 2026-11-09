"""create bookings"""

import sqlalchemy as sa
from alembic import op

revision = "5efe45b2f35f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(12), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booking_time", sa.Time(), nullable=False),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(9), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_bookings_slot", "bookings", ["booking_date", "booking_time", "status"], if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_slot", table_name="bookings")
    op.drop_table("bookings")
