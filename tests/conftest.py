from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    database = (tmp_path / "bookings.db").as_posix()
    url = f"sqlite+aiosqlite:///{database}"
    config = Config("alembic.ini", attributes={"database_url": url})
    command.upgrade(config, "head")
    return url
