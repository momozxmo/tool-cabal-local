from __future__ import annotations

from collections.abc import Iterator

import pytest

from web.db import Database
from web.models import Base
from web.settings import Settings


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    db_path = tmp_path / 'test.db'
    return Settings(
        app_env='test',
        database_url=f'sqlite:///{db_path.as_posix()}',
        app_secret_key='test-secret',
        aztek_encryption_key='test-encryption-key',
        bootstrap_admin_username='admin',
        bootstrap_admin_password='bootstrap-password',
        session_cookie_secure=False,
    )


@pytest.fixture
def test_database(test_settings) -> Iterator[Database]:
    database = Database(test_settings)
    Base.metadata.create_all(database.engine)
    try:
        yield database
    finally:
        Base.metadata.drop_all(database.engine)
        database.engine.dispose()


@pytest.fixture
def db_session(test_database):
    with test_database.session() as session:
        yield session
