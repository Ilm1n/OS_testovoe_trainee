from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.bookings import router
from app.config import Settings


def create_app(database_url: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        url = database_url if database_url is not None else Settings().database_url
        engine = create_async_engine(url)
        try:
            app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Бронирование столиков", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
