import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import create_app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(database_url: str) -> AsyncIterator[AsyncClient]:
    app = create_app(database_url)
    async with (
        LifespanManager(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


def booking_data(days_ahead: int = 1, booking_time: str = "19:00") -> dict[str, str | int]:
    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    return {
        "name": "  Анна Петрова  ",
        "phone": "8 (999) 123-45-67",
        "booking_date": (today + timedelta(days=days_ahead)).isoformat(),
        "booking_time": booking_time,
        "guests": 2,
    }


async def test_create_and_read_bookings(client: AsyncClient) -> None:
    later_data = {**booking_data(days_ahead=90), "name": "José-Марія"}
    later_date = await client.post("/bookings", json=later_data)
    data = booking_data()
    response = await client.post("/bookings", json=data)
    earlier_slot = await client.post("/bookings", json={**data, "booking_time": "12:00"})
    assert [later_date.status_code, response.status_code, earlier_slot.status_code] == [201, 201, 201]

    booking = response.json()
    assert booking["name"] == "Анна Петрова"
    assert booking["phone"] == "+79991234567"
    assert booking["status"] == "active"
    assert booking["booking_time"] == "19:00"
    assert datetime.fromisoformat(booking["created_at"]).utcoffset() == timedelta(0)

    found = await client.get(f"/bookings/{booking['id']}")
    assert found.status_code == 200
    assert found.json() == booking

    listing = await client.get("/bookings")
    assert listing.json() == {"items": [earlier_slot.json(), booking, later_date.json()], "total": 3}
    filtered = await client.get("/bookings", params={"date": data["booking_date"]})
    assert filtered.json() == {"items": [earlier_slot.json(), booking], "total": 2}

    page = await client.get("/bookings", params={"date": data["booking_date"], "limit": 1, "offset": 1})
    assert page.json() == {"items": [booking], "total": 2}
    empty = await client.get("/bookings", params={"date": data["booking_date"], "offset": 2})
    assert empty.json() == {"items": [], "total": 2}

    for missing_id in (999, 2**63):
        missing = await client.get(f"/bookings/{missing_id}")
        assert missing.status_code == 404
        assert missing.json() == {"detail": "Booking not found"}


async def test_invalid_data_returns_422(client: AsyncClient) -> None:
    data = booking_data()
    midnight = datetime.fromisoformat(str(data["booking_date"])).replace(tzinfo=UTC)
    timestamp = int(midnight.timestamp())
    invalid_fields = {
        "name": "A1",
        "phone": "+1 999 123 45 67",
        "booking_date": booking_data(days_ahead=91)["booking_date"],
        "booking_time": "12:00:00",
        "guests": 1.5,
    }
    for field, value in invalid_fields.items():
        response = await client.post("/bookings", json={**data, field: value})
        assert response.status_code == 422, field
        assert isinstance(response.json()["detail"], list)

    assert (await client.get("/bookings/abc")).status_code == 422
    assert (await client.post("/bookings", json={**data, "booking_date": timestamp})).status_code == 422
    assert (await client.get("/bookings", params={"date": timestamp})).status_code == 422
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        assert (await client.get("/bookings", params=params)).status_code == 422


async def test_today_only_future_slots_can_be_booked(client: AsyncClient) -> None:
    now = datetime(2026, 1, 15, 15, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    data = {**booking_data(), "booking_date": now.date().isoformat()}

    with patch("app.schemas.booking.datetime", wraps=datetime) as clock:
        clock.now.side_effect = now.astimezone
        past_slot = await client.post("/bookings", json={**data, "booking_time": "15:00"})
        future_slot = await client.post("/bookings", json={**data, "booking_time": "16:00"})

    assert past_slot.status_code == 422
    assert future_slot.status_code == 201


async def test_cancellation_frees_the_slot(client: AsyncClient) -> None:
    data = booking_data()
    first = await client.post("/bookings", json=data)
    assert first.status_code == 201
    booking = first.json()
    for _ in range(9):
        assert (await client.post("/bookings", json=data)).status_code == 201

    url = f"/bookings/{booking['id']}"
    cancelled = await client.delete(url)
    assert cancelled.status_code == 200
    assert cancelled.json() == {**booking, "status": "cancelled"}
    assert (await client.get(url)).json() == cancelled.json()

    repeated = await client.delete(url)
    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Booking is already cancelled"}
    assert (await client.post("/bookings", json=data)).status_code == 201


async def test_only_one_request_can_book_the_last_table(client: AsyncClient) -> None:
    data = booking_data()
    for _ in range(9):
        assert (await client.post("/bookings", json=data)).status_code == 201

    responses = await asyncio.gather(
        client.post("/bookings", json=data),
        client.post("/bookings", json=data),
    )
    created, conflict = sorted(responses, key=lambda response: response.status_code)
    assert created.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": "Slot is fully booked"}
