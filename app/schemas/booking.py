import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated, Self
from unicodedata import name as unicode_name
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

from app.models.booking import BookingStatus

MOSCOW = ZoneInfo("Europe/Moscow")


def check_date_format(value: object) -> date | str:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return value
    raise ValueError("Укажите дату в формате YYYY-MM-DD")


BookingDate = Annotated[date, BeforeValidator(check_date_format)]


class BookingBase(BaseModel):
    name: str
    phone: str = Field(examples=["+79991234567"])
    booking_date: date
    booking_time: time = Field(examples=["19:00"])
    guests: int


class BookingCreate(BookingBase):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)
    ] = Field(examples=["Анна Петрова"])
    booking_date: BookingDate
    guests: int = Field(strict=True, ge=1, le=12)

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        for character in value:
            if character in " -":
                continue
            if not character.isalpha() or {"LATIN", "CYRILLIC"}.isdisjoint(
                unicode_name(character, "").split()
            ):
                raise ValueError("В имени допустимы латиница, кириллица, пробел и дефис")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        cleaned = re.sub(r"[\s()-]", "", value)
        if not re.fullmatch(r"(?:\+7|8)[0-9]{10}", cleaned):
            raise ValueError("Введите российский номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX")
        return "+7" + cleaned[-10:]

    @field_validator("booking_time", mode="before", json_schema_input_type=str)
    @classmethod
    def check_time(cls, value: object) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"(?:1[2-9]|2[0-2]):00", value):
            raise ValueError("Выберите целый час с 12:00 до 22:00 в формате HH:MM")
        return value

    @model_validator(mode="after")
    def check_slot(self) -> Self:
        now = datetime.now(MOSCOW)
        today = now.date()
        if not today <= self.booking_date <= today + timedelta(days=90):
            raise ValueError("Дата брони должна быть в пределах ближайших 90 дней")
        if datetime.combine(self.booking_date, self.booking_time, tzinfo=MOSCOW) < now:
            raise ValueError("Этот слот уже прошёл")
        return self


class BookingOut(BookingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: BookingStatus
    created_at: datetime

    @field_serializer("booking_time")
    def serialize_time(self, value: time) -> str:
        return value.isoformat(timespec="minutes")

    @field_validator("created_at")
    @classmethod
    def use_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC)


class BookingList(BaseModel):
    items: list[BookingOut]
    total: int
