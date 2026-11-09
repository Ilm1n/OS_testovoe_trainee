FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
WORKDIR /app

ENV UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=sqlite+aiosqlite:////data/bookings.db

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0"]
