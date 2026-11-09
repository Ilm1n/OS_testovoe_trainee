from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import Index, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BookingStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_slot", "booking_date", "booking_time", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(12))
    booking_date: Mapped[date]
    booking_time: Mapped[time]
    guests: Mapped[int]
    status: Mapped[str] = mapped_column(String(9))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
