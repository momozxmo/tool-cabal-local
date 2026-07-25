import base64
# 'inspect' alone is taken by sqlalchemy's below.
import inspect as pyinspect
import os
import shutil
import tempfile
from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError

from web import security
from web.auth_service import AuthService
from web.db import Database
from web.models import User, WebSession, WorkspaceRecord, utc_now
from web.search_coordinator import SearchCoordinator
from web.settings import Settings


PRODUCTION_SETTINGS = {
    'APP_SECRET_KEY': 'app-secret',
    'AZTEK_SESSION_ENCRYPTION_KEY': 'encryption-key',
    'BOOTSTRAP_ADMIN_USERNAME': 'admin',
    'BOOTSTRAP_ADMIN_PASSWORD': 'password',
}

APPLICATION_TABLES = {
    'users', 'web_sessions', 'pairing_tokens', 'aztek_sessions',
    'workspaces', 'pending_imports', 'jobs', 'audit_logs',
}


@pytest.fixture
def settings(test_database):
    return Settings(
        app_env='test',
        database_url=str(test_database.engine.url),
        app_secret_key='task-3-test-secret',
        aztek_encryption_key=base64.urlsafe_b64encode(
            b'k' * 32
        ).decode('ascii'),
        bootstrap_admin_username='Bootstrap.Admin',
        bootstrap_admin_password='bootstrap password',
        session_cookie_secure=False,
        session_ttl_seconds=3600,
    )


@pytest.fixture
def auth_service(settings):
    return AuthService(settings)


@pytest.fixture
def member(auth_service, db_session):
    return auth_service.create_user(
        db_session, ' Member.Name ', 'correct horse', role='member'
    )


def test_password_and_encryption_never_store_plaintext(settings):
    encoded = security.hash_password('correct horse')
    assert 'correct horse' not in encoded
    assert security.verify_password('correct horse', encoded)
    assert not security.verify_password('wrong', encoded)

    state = {
        'cookies': [{'name': 'token', 'value': 'secret'}],
        'origins': [],
    }
    ciphertext = security.encrypt_storage_state(state, settings)
    assert 'secret' not in ciphertext
    assert security.decrypt_storage_state(ciphertext, settings) == state


def test_storage_encryption_uses_random_nonce_and_stable_json(
    monkeypatch, settings
):
    nonce_sizes = []

    def fixed_random(size):
        nonce_sizes.append(size)
        return b'n' * size

    monkeypatch.setattr(security.os, 'urandom', fixed_random)
    first = security.encrypt_storage_state({'b': 2, 'a': 1}, settings)
    second = security.encrypt_storage_state({'a': 1, 'b': 2}, settings)

    assert first == second
    assert nonce_sizes == [12, 12]


def test_storage_decryption_rejects_malformed_and_tampered_state(settings):
    ciphertext = security.encrypt_storage_state({'cookies': []}, settings)
    tampered = bytearray(base64.urlsafe_b64decode(ciphertext.encode('ascii')))
    tampered[-1] ^= 1
    tampered_ciphertext = base64.urlsafe_b64encode(tampered).decode('ascii')

    with pytest.raises(security.InvalidEncryptedState):
        security.decrypt_storage_state('not valid base64!', settings)
    with pytest.raises(security.InvalidEncryptedState):
        security.decrypt_storage_state(tampered_ciphertext, settings)


def test_storage_encryption_requires_decoded_32_byte_key(settings):
    invalid_settings = replace(
        settings,
        aztek_encryption_key=base64.urlsafe_b64encode(b'x' * 31).decode('ascii'),
    )

    with pytest.raises(ValueError, match='32-byte'):
        security.encrypt_storage_state({}, invalid_settings)


def test_storage_encryption_rejects_non_urlsafe_base64_key(settings):
    standard_base64_key = base64.b64encode(b'\xfb' * 32).decode('ascii')
    assert '+' in standard_base64_key or '/' in standard_base64_key
    invalid_settings = replace(
        settings, aztek_encryption_key=standard_base64_key
    )

    with pytest.raises(ValueError, match='URL-safe base64'):
        security.encrypt_storage_state({}, invalid_settings)


def test_create_user_normalizes_identity_and_hashes_password(
    auth_service, db_session
):
    user = auth_service.create_user(
        db_session, ' Mixed.Case-User_1 ', 'ten letters!', role='admin'
    )

    assert user.username == 'mixed.case-user_1'
    assert user.role == 'admin'
    assert user.password_hash != 'ten letters!'
    assert 'ten letters!' not in user.password_hash


@pytest.mark.parametrize(
    'username',
    ['ab', 'a' * 81, 'white space', 'slash/name', 'ภาษาไทย'],
)
def test_create_user_rejects_invalid_username(auth_service, db_session, username):
    with pytest.raises(ValueError, match='username'):
        auth_service.create_user(db_session, username, 'correct horse')


def test_create_user_rejects_short_password_and_unknown_role(
    auth_service, db_session
):
    with pytest.raises(ValueError, match='password'):
        auth_service.create_user(db_session, 'shortpass', 'too short')
    with pytest.raises(ValueError, match='role'):
        auth_service.create_user(
            db_session, 'unknownrole', 'correct horse', role='owner'
        )


def test_create_user_rejects_non_string_role(auth_service, db_session):
    with pytest.raises(ValueError, match='role'):
        auth_service.create_user(
            db_session, 'invalidrole', 'correct horse', role=[]
        )


def test_create_user_rejects_duplicate_normalized_username(
    auth_service, db_session
):
    auth_service.create_user(
        db_session, 'Member.Name', 'correct horse'
    )

    with pytest.raises(IntegrityError):
        auth_service.create_user(
            db_session, ' member.name ', 'correct horse'
        )
    db_session.rollback()


def test_authenticate_accepts_valid_credentials_and_rejects_invalid_or_disabled(
    auth_service, db_session, member
):
    assert member.last_login_at is None
    assert auth_service.authenticate(
        db_session, ' MEMBER.NAME ', 'correct horse'
    ) is member
    assert member.last_login_at is not None
    assert auth_service.authenticate(
        db_session, 'member.name', 'wrong password'
    ) is None

    member.is_active = False
    db_session.flush()
    assert auth_service.authenticate(
        db_session, 'member.name', 'correct horse'
    ) is None


def test_session_token_is_stored_as_hmac_hash(
    auth_service, db_session, member, settings
):
    raw = auth_service.create_session(db_session, member)
    record = db_session.scalar(
        select(WebSession).where(WebSession.user_id == member.id)
    )

    assert record is not None
    assert raw != record.token_hash
    assert record.token_hash == security.hash_token(raw, settings)
    assert record.expires_at > utc_now() + timedelta(minutes=59)
    assert auth_service.resolve_session(db_session, raw).id == member.id
    assert record.last_seen_at is not None


def test_expired_revoked_and_disabled_sessions_do_not_resolve(
    auth_service, db_session, member
):
    expired_token = auth_service.create_session(db_session, member)
    expired_record = db_session.scalar(
        select(WebSession).where(
            WebSession.token_hash == security.hash_token(
                expired_token, auth_service.settings
            )
        )
    )
    expired_record.expires_at = utc_now() - timedelta(seconds=1)
    db_session.flush()
    assert auth_service.resolve_session(db_session, expired_token) is None

    revoked_token = auth_service.create_session(db_session, member)
    auth_service.revoke_session(db_session, revoked_token)
    assert auth_service.resolve_session(db_session, revoked_token) is None

    disabled_token = auth_service.create_session(db_session, member)
    member.is_active = False
    db_session.flush()
    assert auth_service.resolve_session(db_session, disabled_token) is None


def test_revoke_session_revokes_only_the_supplied_token(
    auth_service, db_session, member
):
    revoked_token = auth_service.create_session(db_session, member)
    remaining_token = auth_service.create_session(db_session, member)

    auth_service.revoke_session(db_session, revoked_token)

    assert auth_service.resolve_session(db_session, revoked_token) is None
    assert (
        auth_service.resolve_session(db_session, remaining_token).id == member.id
    )


def test_revoke_all_sessions_revokes_only_selected_user(
    auth_service, db_session, member
):
    other = auth_service.create_user(
        db_session, 'other.member', 'correct horse'
    )
    member_tokens = [
        auth_service.create_session(db_session, member),
        auth_service.create_session(db_session, member),
    ]
    other_token = auth_service.create_session(db_session, other)

    auth_service.revoke_all_sessions(db_session, member.id)

    assert all(
        auth_service.resolve_session(db_session, token) is None
        for token in member_tokens
    )
    assert auth_service.resolve_session(db_session, other_token).id == other.id


def test_bootstrap_admin_requires_credentials_and_an_empty_user_table(
    settings, db_session
):
    missing_credentials = AuthService(
        replace(settings, bootstrap_admin_password='')
    )
    assert missing_credentials.bootstrap_admin(db_session) is None
    missing_username = AuthService(
        replace(settings, bootstrap_admin_username='   ')
    )
    assert missing_username.bootstrap_admin(db_session) is None

    service = AuthService(settings)
    admin = service.bootstrap_admin(db_session)
    assert admin is not None
    assert admin.username == 'bootstrap.admin'
    assert admin.role == 'admin'
    assert service.bootstrap_admin(db_session) is None


def configure_production(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    for name, value in PRODUCTION_SETTINGS.items():
        monkeypatch.setenv(name, value)


def test_settings_default_to_local_sqlite(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        settings = Settings.from_env()
    assert settings.database_url == 'sqlite:///./all_for_cabal_web.db'
    assert settings.browser_concurrency == 1


@pytest.mark.parametrize('missing_setting', PRODUCTION_SETTINGS)
def test_production_rejects_each_missing_secret(monkeypatch, missing_setting):
    configure_production(monkeypatch)
    monkeypatch.delenv(missing_setting)
    with pytest.raises(ValueError, match=missing_setting):
        Settings.from_env()


def test_production_forces_secure_session_cookie(monkeypatch):
    configure_production(monkeypatch)
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'false')
    settings = Settings.from_env()
    assert settings.session_cookie_secure is True


def test_development_warns_about_process_local_secrets(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        Settings.from_env()


def test_malformed_browser_concurrency_is_rejected(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('BROWSER_CONCURRENCY', 'many')
    with pytest.warns(RuntimeWarning, match='sessions will not survive restart'):
        with pytest.raises(ValueError, match='BROWSER_CONCURRENCY must be an integer'):
            Settings.from_env()


def test_alembic_migration_creates_and_removes_application_schema(monkeypatch):
    tmpdir = tempfile.mkdtemp(prefix='afc_test_')
    database_url = 'sqlite:///%s' % os.path.join(tmpdir, 'migration.db').replace('\\', '/')
    configure_production(monkeypatch)
    monkeypatch.setenv('DATABASE_URL', database_url)
    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
    engine = create_engine(database_url)

    try:
        command.upgrade(config, 'head')
        schema = inspect(engine)

        assert APPLICATION_TABLES <= set(schema.get_table_names())

        def foreign_keys(table_name):
            return {
                (tuple(item['constrained_columns']), item['referred_table'],
                 tuple(item['referred_columns']))
                for item in schema.get_foreign_keys(table_name)
            }

        def unique_columns(table_name):
            constraints = {
                tuple(item['column_names'])
                for item in schema.get_unique_constraints(table_name)
            }
            indexes = {
                tuple(item['column_names'])
                for item in schema.get_indexes(table_name)
                if item['unique']
            }
            return constraints | indexes

        assert ('username',) in unique_columns('users')
        assert ('token_hash',) in unique_columns('web_sessions')
        assert ('token_hash',) in unique_columns('pairing_tokens')
        assert ('user_id',) in unique_columns('aztek_sessions')
        assert (('user_id',), 'users', ('id',)) in foreign_keys('web_sessions')
        assert (('user_id',), 'users', ('id',)) in foreign_keys('pairing_tokens')
        assert (('user_id',), 'users', ('id',)) in foreign_keys('aztek_sessions')
        assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('workspaces')
        assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('pending_imports')
        assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('pending_imports')
        assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('jobs')
        assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('jobs')
        assert (('user_id',), 'users', ('id',)) in foreign_keys('audit_logs')

        command.downgrade(config, 'base')
        assert not (APPLICATION_TABLES & set(inspect(engine).get_table_names()))
    finally:
        engine.dispose()
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_schema_creates_all_security_and_job_tables(test_database):
    names = set(inspect(test_database.engine).get_table_names())
    assert {
        'users', 'web_sessions', 'pairing_tokens', 'aztek_sessions',
        'workspaces', 'pending_imports', 'jobs', 'audit_logs',
    } <= names


def test_schema_enforces_identity_and_ownership_constraints(test_database):
    schema = inspect(test_database.engine)

    def foreign_keys(table_name):
        return {
            (tuple(item['constrained_columns']), item['referred_table'],
             tuple(item['referred_columns']))
            for item in schema.get_foreign_keys(table_name)
        }

    def unique_columns(table_name):
        constraints = {
            tuple(item['column_names'])
            for item in schema.get_unique_constraints(table_name)
        }
        indexes = {
            tuple(item['column_names'])
            for item in schema.get_indexes(table_name)
            if item['unique']
        }
        return constraints | indexes

    assert ('username',) in unique_columns('users')
    assert ('token_hash',) in unique_columns('web_sessions')
    assert ('token_hash',) in unique_columns('pairing_tokens')
    assert ('user_id',) in unique_columns('aztek_sessions')

    assert (('user_id',), 'users', ('id',)) in foreign_keys('web_sessions')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('pairing_tokens')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('aztek_sessions')
    assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('workspaces')
    assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('pending_imports')
    assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('pending_imports')
    job_columns = {column['name'] for column in schema.get_columns('jobs')}
    assert 'owner_user_id' in job_columns
    assert 'user_id' not in job_columns
    assert (('owner_user_id',), 'users', ('id',)) in foreign_keys('jobs')
    assert (('workspace_id',), 'workspaces', ('id',)) in foreign_keys('jobs')
    assert (('user_id',), 'users', ('id',)) in foreign_keys('audit_logs')
    audit_user_id = next(
        column for column in schema.get_columns('audit_logs')
        if column['name'] == 'user_id'
    )
    assert audit_user_id['nullable'] is True


def test_database_session_commits_and_rolls_back(test_database):
    committed_id = '2' * 32
    rolled_back_id = '3' * 32

    with test_database.session() as session:
        session.add(User(
            id=committed_id, username='committed', password_hash='hash'))

    with test_database.session() as session:
        assert session.get(User, committed_id) is not None

    with pytest.raises(RuntimeError, match='trigger rollback'):
        with test_database.session() as session:
            session.add(User(
                id=rolled_back_id, username='rolled-back', password_hash='hash'))
            session.flush()
            raise RuntimeError('trigger rollback')

    with test_database.session() as session:
        assert session.get(User, rolled_back_id) is None


def test_sqlite_enforces_foreign_keys_for_orphan_records(test_database):
    with pytest.raises(IntegrityError):
        with test_database.session() as session:
            session.add(WorkspaceRecord(
                owner_user_id='9' * 32,
                mode='event',
                filename='orphan.xlsx',
            ))
            session.flush()


def test_timestamps_round_trip_as_utc_aware_values(db_session):
    db_session.add(User(id='1' * 32, username='member', password_hash='hash'))
    db_session.flush()
    db_session.expunge_all()

    user = db_session.get(User, '1' * 32)
    assert user is not None
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset().total_seconds() == 0


def test_timestamps_reject_naive_input(test_database):
    with pytest.raises(StatementError) as error:
        with test_database.session() as session:
            session.add(User(
                id='4' * 32,
                username='naive',
                password_hash='hash',
                password_changed_at=datetime(2026, 1, 1, 12, 0, 0),
            ))
            session.flush()
    assert isinstance(error.value.orig, ValueError)
    assert 'timezone-aware' in str(error.value.orig)


def test_headed_search_is_refused_in_production(settings, test_database):
    """A hosted server has no display, so it must ignore a headed request."""
    coordinator = SearchCoordinator(test_database, settings, aztek_session_service=None)
    assert coordinator.resolve_headed(True) is True
    assert coordinator.resolve_headed(False) is False

    hosted = SearchCoordinator(
        test_database, replace(settings, app_env='production'),
        aztek_session_service=None)
    assert hosted.resolve_headed(True) is False
    assert hosted.resolve_headed(False) is False


def test_the_socket_only_watches_the_search_it_asked_for():
    """Create Bundle is a page of its own now, so leaving mid-search is normal.

    The run has to belong to the application, not to the socket: the endpoint
    starts it and then subscribes, and only an explicit stop cancels it.
    """
    start = pyinspect.getsource(SearchCoordinator.start)
    assert 'ensure_future' in start, 'the run must outlive the caller'
    assert '_cancel' not in start
    # Cancelling is its own request now.
    assert '_cancel = True' in pyinspect.getsource(SearchCoordinator.stop)
    # And a run cannot survive the process, so nothing may be left claiming to.
    assert 'failed' in pyinspect.getsource(SearchCoordinator.sweep_interrupted_jobs)
