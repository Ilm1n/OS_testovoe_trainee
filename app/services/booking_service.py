from datetime import date

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.schemas.booking import BookingCreate

SLOT_CAPACITY = 10


class BookingNotFound(Exception):
    pass


class SlotFull(Exception):
    pass


class BookingAlreadyCancelled(Exception):
    pass


async def create_booking(session: AsyncSession, data: BookingCreate) -> Booking:
    async with session.begin():
        await session.execute(text("BEGIN IMMEDIATE"))
        result = await session.execute(
            select(func.count(Booking.id)).where(
                Booking.booking_date == data.booking_date,
                Booking.booking_time == data.booking_time,
                Booking.status == BookingStatus.ACTIVE,
            )
        )
        if result.scalar_one() >= SLOT_CAPACITY:
            raise SlotFull

        booking = Booking(
            name=data.name,
            phone=data.phone,
            booking_date=data.booking_date,
            booking_time=data.booking_time,
            guests=data.guests,
            status=BookingStatus.ACTIVE,
        )
        session.add(booking)
    return booking


async def list_bookings(
    session: AsyncSession,
    booking_date: date | None,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Booking], int]:
    query = select(Booking)
    if booking_date is not None:
        query = query.where(Booking.booking_date == booking_date)

    async with session.begin():
        await session.execute(text("BEGIN"))
        count = await session.execute(query.with_only_columns(func.count(Booking.id)))
        total = count.scalar_one()
        if offset >= total:
            return [], total

        page = query.order_by(Booking.booking_date, Booking.booking_time, Booking.id)
        bookings = await session.scalars(page.limit(limit).offset(offset))
        return list(bookings), total


async def get_booking(session: AsyncSession, booking_id: int) -> Booking:
    if not 1 <= booking_id < 2**63:
        raise BookingNotFound
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise BookingNotFound
    return booking


async def cancel_booking(session: AsyncSession, booking_id: int) -> Booking:
    async with session.begin():
        await session.execute(text("BEGIN IMMEDIATE"))
        booking = await get_booking(session, booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise BookingAlreadyCancelled
        booking.status = BookingStatus.CANCELLED
    return booking
