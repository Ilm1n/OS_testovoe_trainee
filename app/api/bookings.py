from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingDate, BookingList, BookingOut
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Slot is fully booked"}},
)
async def create_booking(data: BookingCreate, session: Session) -> Booking:
    try:
        return await booking_service.create_booking(session, data)
    except booking_service.SlotFull as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is fully booked") from exc


@router.get("", response_model=BookingList)
async def list_bookings(
    session: Session,
    booking_date: Annotated[BookingDate | None, Query(alias="date")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BookingList:
    bookings, total = await booking_service.list_bookings(
        session, booking_date, limit=limit, offset=offset
    )
    items = [BookingOut.model_validate(booking) for booking in bookings]
    return BookingList(items=items, total=total)

        
@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    responses={404: {"description": "Booking not found"}},
)
async def get_booking(booking_id: int, session: Session) -> Booking:
    try:
        return await booking_service.get_booking(session, booking_id)
    except booking_service.BookingNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found") from exc


@router.delete(
    "/{booking_id}",
    response_model=BookingOut,
    responses={
        404: {"description": "Booking not found"},
        409: {"description": "Booking is already cancelled"},
    },
)
async def cancel_booking(booking_id: int, session: Session) -> Booking:
    try:
        return await booking_service.cancel_booking(session, booking_id)
    except booking_service.BookingNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found") from exc
    except booking_service.BookingAlreadyCancelled as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Booking is already cancelled") from exc
