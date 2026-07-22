from collections import Counter

from fastapi import Depends
from fastapi.testclient import TestClient

from web import app as web_app
from web.auth_service import AuthService
from web.models import User


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
