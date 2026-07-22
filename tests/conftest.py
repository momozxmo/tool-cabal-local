from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from web import app as web_app
from web.db import Database
from web.models import Base, User
from web.settings import Settings
from web.workspaces import WorkspaceRepository


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


@pytest.fixture
def application(test_settings, test_database):
    return web_app.create_app(test_settings, test_database)


@pytest.fixture
def anonymous_client(application):
    return TestClient(application)


@pytest.fixture
def member(application, test_database):
    with test_database.session() as db:
        return application.state.auth_service.create_user(
            db, 'workspace.member', 'correct horse'
        )


@pytest.fixture
def other_member(application, test_database):
    with test_database.session() as db:
        return application.state.auth_service.create_user(
            db, 'workspace.other', 'correct horse'
        )


@pytest.fixture
def client_for(application, test_database):
    def make_client(user: User) -> TestClient:
        with test_database.session() as db:
            persisted_user = db.get(User, user.id)
            assert persisted_user is not None
            token = application.state.auth_service.create_session(db, persisted_user)
        client = TestClient(application)
        client.cookies.set('afc_session', token)
        return client

    return make_client


@pytest.fixture
def client(client_for, member):
    return client_for(member)


@pytest.fixture
def workspace_for_member(test_database, member):
    with test_database.session() as db:
        return WorkspaceRepository(db).create(member.id, 'event', 'owned.xlsx')
