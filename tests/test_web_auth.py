from collections import Counter
from dataclasses import replace

from fastapi import Depends
from fastapi.testclient import TestClient

from web import app as web_app
from web.auth_service import AuthService
from web.models import User


AUTH_FAILURE_MESSAGE = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'


class MonotonicClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def _client(application):
    return TestClient(application, follow_redirects=False)


def _create_user(application, database, username='member.user', password='correct horse'):
    with database.session() as db:
        return application.state.auth_service.create_user(db, username, password)


def _login(client, username='member.user', password='correct horse'):
    return client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })


def test_create_app_uses_injected_dependencies(test_settings, test_database):
    application = web_app.create_app(test_settings, test_database)

    assert application.state.settings is test_settings
    assert application.state.database is test_database
    assert isinstance(application.state.auth_service, AuthService)
    assert application.state.auth_service.settings is test_settings


def test_create_app_has_isolated_state_and_registers_routes_once(
    test_settings, test_database
):
    first = web_app.create_app(test_settings, test_database)
    second = web_app.create_app(test_settings, test_database)

    assert first is not second
    assert first.state is not second.state
    assert first.state.auth_service is not second.state.auth_service

    first_routes = [(route.path, route.name) for route in first.routes]
    second_routes = [(route.path, route.name) for route in second.routes]
    assert first_routes == second_routes
    assert Counter(first_routes).most_common(1)[0][1] == 1
    assert '/api/health' in {path for path, _name in first_routes}
    assert '/ws/search' in {path for path, _name in first_routes}


def _add_auth_probe_routes(application):
    get_db = getattr(web_app, 'get_db', None)
    require_user = getattr(web_app, 'require_user', None)
    require_admin = getattr(web_app, 'require_admin', None)
    assert callable(get_db), 'get_db is required'
    assert callable(require_user), 'require_user is required'
    assert callable(require_admin), 'require_admin is required'

    @application.get('/__test/current-user')
    def current_user(user: User = Depends(require_user)):
        return {'username': user.username, 'role': user.role}

    @application.get('/__test/database-user/{user_id}')
    def database_user(user_id: str, db=Depends(get_db)):
        user = db.get(User, user_id)
        return {'username': user.username if user else None}

    @application.get('/__test/admin')
    def admin_only(user: User = Depends(require_admin)):
        return {'username': user.username}


def test_require_user_resolves_valid_cookie_and_rejects_missing_or_invalid(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    _add_auth_probe_routes(application)
    service = application.state.auth_service
    with test_database.session() as db:
        member = service.create_user(db, 'member.user', 'correct horse')
        token = service.create_session(db, member)
        member_id = member.id

    client = TestClient(application)
    missing = client.get('/__test/current-user')
    client.cookies.set('afc_session', 'invalid')
    invalid = client.get('/__test/current-user')
    client.cookies.set('afc_session', token)
    valid = client.get('/__test/current-user')
    database_user = client.get('/__test/database-user/' + member_id)

    assert missing.status_code == 401
    assert missing.json() == {'detail': 'กรุณาเข้าสู่ระบบ'}
    assert invalid.status_code == 401
    assert invalid.json() == {'detail': 'กรุณาเข้าสู่ระบบ'}
    assert valid.status_code == 200
    assert valid.json() == {'username': 'member.user', 'role': 'member'}
    assert database_user.json() == {'username': 'member.user'}


def test_require_admin_allows_admin_and_rejects_member(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    _add_auth_probe_routes(application)
    service = application.state.auth_service
    with test_database.session() as db:
        admin = service.create_user(
            db, 'admin.user', 'correct horse', role='admin'
        )
        member = service.create_user(db, 'member.user', 'correct horse')
        admin_token = service.create_session(db, admin)
        member_token = service.create_session(db, member)

    client = TestClient(application)
    client.cookies.set('afc_session', admin_token)
    admin_response = client.get('/__test/admin')
    client.cookies.set('afc_session', member_token)
    member_response = client.get('/__test/admin')

    assert admin_response.status_code == 200
    assert admin_response.json() == {'username': 'admin.user'}
    assert member_response.status_code == 403
    assert member_response.json() == {'detail': 'ไม่มีสิทธิ์ใช้งานส่วนนี้'}


def test_login_returns_safe_user_and_session_cookie(test_settings, test_database):
    application = web_app.create_app(test_settings, test_database)
    user = _create_user(application, test_database)

    response = _login(_client(application))

    assert response.status_code == 200
    assert response.json() == {
        'id': user.id,
        'username': 'member.user',
        'role': 'member',
        'is_active': True,
    }
    cookie = response.headers['set-cookie'].lower()
    assert 'afc_session=' in cookie
    assert 'httponly' in cookie
    assert 'path=/' in cookie
    assert 'samesite=lax' in cookie
    assert 'max-age=604800' in cookie
    assert 'secure' not in cookie


def test_login_uses_one_generic_failure_for_unknown_wrong_and_disabled(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    user = _create_user(application, test_database)
    with test_database.session() as db:
        db.get(User, user.id).is_active = False
    client = _client(application)

    responses = [
        _login(client, 'unknown.user'),
        _login(client, password='wrong password'),
        _login(client),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]
    assert [response.json() for response in responses] == [
        {'detail': AUTH_FAILURE_MESSAGE},
        {'detail': AUTH_FAILURE_MESSAGE},
        {'detail': AUTH_FAILURE_MESSAGE},
    ]


def test_login_cookie_is_secure_when_settings_require_it(test_settings, test_database):
    settings = replace(test_settings, app_env='production', session_cookie_secure=True)
    application = web_app.create_app(settings, test_database)
    _create_user(application, test_database)

    response = _login(_client(application))

    assert response.status_code == 200
    assert 'secure' in response.headers['set-cookie'].lower()


def test_login_throttle_allows_five_failures_then_returns_429_and_success_resets(
    test_settings, test_database
):
    clock = MonotonicClock()
    application = web_app.create_app(test_settings, test_database, monotonic_clock=clock)
    _create_user(application, test_database)
    client = _client(application)

    for _ in range(4):
        assert _login(client, password='wrong password').status_code == 401
    assert _login(client).status_code == 200
    for _ in range(5):
        assert _login(client, password='wrong password').status_code == 401
    limited = _login(client, password='wrong password')

    assert limited.status_code == 429
    assert limited.json() == {'detail': 'ลองใหม่ภายหลัง'}


def test_me_requires_a_session_and_returns_only_safe_user_fields(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    user = _create_user(application, test_database)
    client = _client(application)

    missing = client.get('/api/auth/me')
    logged_in = _login(client)
    authenticated = client.get('/api/auth/me')

    assert missing.status_code == 401
    assert logged_in.status_code == 200
    assert authenticated.json() == {
        'id': user.id,
        'username': user.username,
        'role': 'member',
        'is_active': True,
    }


def test_logout_revokes_session_and_clears_cookie(test_settings, test_database):
    application = web_app.create_app(test_settings, test_database)
    _create_user(application, test_database)
    client = _client(application)
    assert _login(client).status_code == 200

    response = client.post('/api/auth/logout')

    assert response.status_code == 204
    assert 'afc_session=""' in response.headers['set-cookie'].lower()
    assert 'max-age=0' in response.headers['set-cookie'].lower()
    assert client.get('/api/auth/me').status_code == 401


def test_production_cookie_deletion_is_secure_for_logout_and_password_change(
    test_settings, test_database
):
    settings = replace(test_settings, app_env='production', session_cookie_secure=True)
    application = web_app.create_app(settings, test_database)
    _create_user(application, test_database)
    client = TestClient(
        application,
        base_url='https://testserver',
        follow_redirects=False,
    )

    assert _login(client).status_code == 200
    logged_out = client.post('/api/auth/logout')
    assert _login(client).status_code == 200
    password_changed = client.post('/api/auth/change-password', json={
        'current_password': 'correct horse',
        'new_password': 'a better password',
    })

    for response in (logged_out, password_changed):
        assert response.status_code == 204
        cookie = response.headers['set-cookie'].lower()
        assert 'secure' in cookie
        assert 'httponly' in cookie
        assert 'samesite=lax' in cookie
        assert 'path=/' in cookie


def test_change_password_rejects_wrong_password_and_revokes_all_sessions(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    user = _create_user(application, test_database)
    service = application.state.auth_service
    with test_database.session() as db:
        first_token = service.create_session(db, db.get(User, user.id))
        second_token = service.create_session(db, db.get(User, user.id))
        password_changed_at = db.get(User, user.id).password_changed_at
    client = _client(application)
    client.cookies.set('afc_session', first_token)

    wrong = client.post('/api/auth/change-password', json={
        'current_password': 'wrong password',
        'new_password': 'a better password',
    })
    changed = client.post('/api/auth/change-password', json={
        'current_password': 'correct horse',
        'new_password': 'a better password',
    })

    assert wrong.status_code == 400
    assert wrong.json() == {'detail': 'ไม่สามารถเปลี่ยนรหัสผ่านได้'}
    assert changed.status_code == 204
    assert 'max-age=0' in changed.headers['set-cookie'].lower()
    with test_database.session() as db:
        updated = db.get(User, user.id)
        assert updated.password_hash != user.password_hash
        assert updated.password_changed_at > password_changed_at
        assert service.resolve_session(db, first_token) is None
        assert service.resolve_session(db, second_token) is None
    assert _login(_client(application), password='correct horse').status_code == 401
    assert _login(_client(application), password='a better password').status_code == 200


def test_bootstrap_runs_only_for_an_empty_migrated_user_table(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    with TestClient(application):
        pass
    with test_database.session() as db:
        users = list(db.query(User).order_by(User.username))
        assert [(user.username, user.role) for user in users] == [('admin', 'admin')]

    existing = web_app.create_app(test_settings, test_database)
    with TestClient(existing):
        pass
    with test_database.session() as db:
        assert db.query(User).count() == 1


def test_root_redirects_anonymous_but_serves_existing_item_finder_after_login(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    _create_user(application, test_database)
    client = _client(application)

    anonymous = client.get('/')
    assert _login(client).status_code == 200
    authenticated = client.get('/')

    assert anonymous.status_code in (302, 303, 307)
    assert anonymous.headers['location'] == '/login'
    assert authenticated.status_code == 200
    assert 'All for Cabal' in authenticated.text


def test_login_and_account_page_routes_follow_authentication_state(
    test_settings, test_database
):
    application = web_app.create_app(test_settings, test_database)
    _create_user(application, test_database)
    client = _client(application)

    anonymous_login = client.get('/login')
    anonymous_account = client.get('/account')
    assert _login(client).status_code == 200
    authenticated_login = client.get('/login')
    authenticated_account = client.get('/account')

    assert anonymous_login.status_code == 200
    assert 'loginForm' in anonymous_login.text
    assert anonymous_account.status_code in (302, 303, 307)
    assert anonymous_account.headers['location'] == '/login'
    assert authenticated_login.status_code in (302, 303, 307)
    assert authenticated_login.headers['location'] == '/'
    assert authenticated_account.status_code == 200
    assert 'changePasswordForm' in authenticated_account.text


def test_item_finder_apis_require_authentication(test_settings, test_database):
    application = web_app.create_app(test_settings, test_database)

    response = _client(application).get('/api/modes')

    assert response.status_code == 401
    assert response.headers['content-type'].startswith('application/json')
