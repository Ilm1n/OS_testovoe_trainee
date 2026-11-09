from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.schemas.booking import BookingCreate
from app.services.booking_service import SlotFull, create_booking


@pytest.mark.asyncio
async def test_full_slot_does_not_block_other_slots(database_url: str) -> None:
    tomorrow = datetime.now(ZoneInfo("Europe/Moscow")).date() + timedelta(days=1)
    data = {
        "name": "Анна Петрова",
        "phone": "+79991234567",
        "booking_date": tomorrow.isoformat(),
        "booking_time": "19:00",
        "guests": 2,
    }
    slot = BookingCreate.model_validate(data)
    another_time = BookingCreate.model_validate({**data, "booking_time": "20:00"})
    another_date = BookingCreate.model_validate(
        {**data, "booking_date": (tomorrow + timedelta(days=1)).isoformat()}
    )

    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            for _ in range(10):
                await create_booking(session, slot)

            with pytest.raises(SlotFull):
                await create_booking(session, slot)

            assert (await create_booking(session, another_time)).booking_time == another_time.booking_time
            assert (await create_booking(session, another_date)).booking_date == another_date.booking_date
    finally:
        await engine.dispose()
