# -*- coding: utf-8 -*-
"""All for Cabal Web — local Item Finder application."""
import asyncio
import hashlib
import hmac
import os
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import (APIRouter, Cookie, Depends, FastAPI, File, Form,
                     HTTPException, Request, Response, UploadFile, WebSocket,
                     WebSocketDisconnect)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aztek_core as core  # noqa: E402
import item_finder  # noqa: E402
from web import item_service, search_runner  # noqa: E402
from web.audit import write_audit  # noqa: E402
from web.auth_service import AuthService  # noqa: E402
from web.aztek_sessions import (AztekSessionService, InvalidStorageState,  # noqa: E402
                                PairingTokenNotFound, PairingTokenUnavailable)
from web.db import Database  # noqa: E402
from web.models import User, utc_now  # noqa: E402
from web.security import hash_password, hash_token, verify_password  # noqa: E402
from web.settings import Settings  # noqa: E402
from web.workspaces import (PendingImportNotFound, WorkspaceNotFound,
                            WorkspaceRepository)  # noqa: E402


router = APIRouter()
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
# Retained for compatibility with legacy callers; handlers never use it as data.
WORKSPACES = item_service.WorkspaceStore()
Mode = Literal['event', 'itemcode', 'shop']


class ApplyPlanRequest(BaseModel):
    pending_id: str
    selected_sheets: list[str]


class BundleRequest(BaseModel):
    selected_indexes: list[int] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class StorageStatePayload(BaseModel):
    pairing_token: str = Field(min_length=20, max_length=200)
    account_label: str | None = Field(default=None, max_length=120)
    storage_state: dict


class LoginThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_limited(self, client_ip: str) -> bool:
        with self._lock:
            return len(self._recent_failures(client_ip)) >= 5

    def record_failure(self, client_ip: str) -> None:
        with self._lock:
            self._recent_failures(client_ip).append(self._clock())

    def clear(self, client_ip: str) -> None:
        with self._lock:
            self._failures.pop(client_ip, None)

    def _recent_failures(self, client_ip: str) -> list[float]:
        cutoff = self._clock() - 600
        failures = [
            occurred_at
            for occurred_at in self._failures.get(client_ip, [])
            if occurred_at > cutoff
        ]
        self._failures[client_ip] = failures
        return failures


def _safe_user(user: User) -> dict[str, str | bool]:
    return {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'is_active': user.is_active,
    }


def _login_username_fingerprint(username: str, request: Request) -> str:
    key = request.app.state.settings.app_secret_key.encode('utf-8')
    normalized = username.strip().casefold().encode('utf-8')
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()[:32]


def _set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        'afc_session',
        raw_token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite='lax',
        path='/',
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        'afc_session',
        path='/',
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite='lax',
    )


def get_db(request: Request):
    with request.app.state.database.session() as db:
        yield db


def require_user(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    user = request.app.state.auth_service.resolve_session(db, afc_session)
    if user is None:
        raise HTTPException(status_code=401, detail='กรุณาเข้าสู่ระบบ')
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='ไม่มีสิทธิ์ใช้งานส่วนนี้')
    return user


def _workspace_view(workspace):
    return {
        'workspace_id': workspace.id,
        'mode': workspace.mode,
        'filename': workspace.filename,
        'count': len(workspace.criteria),
        'items': workspace.criteria,
        'occurrence_count': len(workspace.occurrences),
        'skipped': workspace.skipped,
        'result_count': len(workspace.results),
        'results': [search_runner.result_view(row) for row in workspace.results],
        'not_found': workspace.not_found,
        'policy': item_service.mode_policy(workspace.mode),
    }


def _get_workspace(repository: WorkspaceRepository, user_id: str, workspace_id: str):
    try:
        return repository.get_owned(user_id, workspace_id)
    except WorkspaceNotFound:
        raise HTTPException(status_code=404, detail='ไม่พบงาน Item Finder นี้')


async def _temporary_upload(file):
    suffix = os.path.splitext(file.filename or '')[1] or '.xlsx'
    raw = await file.read()
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        handle.write(raw)
        handle.close()
    except Exception:
        handle.close()
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
    return handle.name


@router.get('/', response_class=HTMLResponse)
def index(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = request.app.state.auth_service.resolve_session(db, afc_session)
    if user is None:
        return RedirectResponse('/login')
    with open(os.path.join(STATIC_DIR, 'index.html'), encoding='utf-8') as stream:
        return stream.read()


@router.get('/login', response_class=HTMLResponse)
def login_page(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = request.app.state.auth_service.resolve_session(db, afc_session)
    if user is not None:
        return RedirectResponse('/')
    with open(os.path.join(STATIC_DIR, 'login.html'), encoding='utf-8') as stream:
        return stream.read()


@router.get('/account', response_class=HTMLResponse)
def account_page(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = request.app.state.auth_service.resolve_session(db, afc_session)
    if user is None:
        return RedirectResponse('/login')
    with open(os.path.join(STATIC_DIR, 'account.html'), encoding='utf-8') as stream:
        return stream.read()


@router.post('/api/auth/login')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else 'unknown'
    throttle: LoginThrottle = request.app.state.login_throttle
    if throttle.is_limited(client_ip):
        write_audit(
            db,
            user_id=None,
            action='auth.login_failed',
            status='failure',
            summary={
                'reason': 'throttled',
                'target_username': _login_username_fingerprint(payload.username, request),
            },
            tool='auth',
            request=request,
        )
        return JSONResponse({'detail': 'ลองใหม่ภายหลัง'}, status_code=429)
    user = request.app.state.auth_service.authenticate(
        db, payload.username, payload.password
    )
    if user is None:
        throttle.record_failure(client_ip)
        write_audit(
            db,
            user_id=None,
            action='auth.login_failed',
            status='failure',
            summary={
                'reason': 'invalid_credentials',
                'target_username': _login_username_fingerprint(payload.username, request),
            },
            tool='auth',
            request=request,
        )
        return JSONResponse(
            {'detail': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status_code=401
        )
    throttle.clear(client_ip)
    response = JSONResponse(_safe_user(user))
    _set_session_cookie(
        response,
        request.app.state.auth_service.create_session(db, user),
        request.app.state.settings,
    )
    write_audit(
        db,
        user_id=user.id,
        action='auth.login_succeeded',
        status='success',
        summary={'role': user.role},
        tool='auth',
        resource_type='user',
        resource_id=user.id,
        request=request,
    )
    return response


@router.post('/api/auth/logout', status_code=204)
def logout(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = request.app.state.auth_service.resolve_session(db, afc_session)
    request.app.state.auth_service.revoke_session(db, afc_session)
    write_audit(
        db,
        user_id=user.id if user is not None else None,
        action='auth.logout',
        status='success',
        summary={'role': user.role} if user is not None else {},
        tool='auth',
        resource_type='user' if user is not None else '',
        resource_id=user.id if user is not None else '',
        request=request,
    )
    response = Response(status_code=204)
    _clear_session_cookie(response, request.app.state.settings)
    return response


@router.get('/api/auth/me')
def me(user: User = Depends(require_user)):
    return _safe_user(user)


@router.post('/api/auth/change-password', status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if (
        not verify_password(payload.current_password, user.password_hash)
        or len(payload.new_password) < 10
    ):
        raise HTTPException(status_code=400, detail='ไม่สามารถเปลี่ยนรหัสผ่านได้')
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utc_now()
    request.app.state.auth_service.revoke_all_sessions(db, user.id)
    response = Response(status_code=204)
    _clear_session_cookie(response, request.app.state.settings)
    return response


@router.post('/api/aztek/pairing-token')
def create_pairing_token(request: Request, user: User = Depends(require_user),
                         db: Session = Depends(get_db)):
    issue = request.app.state.aztek_session_service.create_pairing_token(db, user)
    write_audit(
        db, user_id=user.id, action='aztek.pairing_requested', status='success',
        tool='aztek', resource_type='aztek_session', resource_id=user.id,
        request=request,
    )
    return {'pairing_token': issue.raw_token, 'expires_at': issue.expires_at.isoformat()}


@router.post('/api/aztek/pair')
def pair_aztek_session(payload: StorageStatePayload, request: Request,
                       db: Session = Depends(get_db)):
    # The only endpoint authenticated by pairing token instead of a cookie.
    client_ip = request.client.host if request.client else 'unknown'
    settings: Settings = request.app.state.settings
    throttle: LoginThrottle = request.app.state.pairing_throttle
    throttle_key = '%s|%s' % (
        client_ip, hash_token(payload.pairing_token, settings))
    if throttle.is_limited(throttle_key):
        return JSONResponse({'detail': 'ลองใหม่ภายหลัง'}, status_code=429)

    service: AztekSessionService = request.app.state.aztek_session_service
    try:
        session = service.consume_pairing_token(
            db, payload.pairing_token, payload.storage_state, payload.account_label)
    except PairingTokenNotFound:
        throttle.record_failure(throttle_key)
        raise HTTPException(status_code=404, detail='ไม่พบรหัสจับคู่')
    except PairingTokenUnavailable:
        throttle.record_failure(throttle_key)
        raise HTTPException(status_code=410, detail='รหัสจับคู่หมดอายุหรือถูกใช้ไปแล้ว')
    except InvalidStorageState:
        throttle.record_failure(throttle_key)
        raise HTTPException(status_code=422, detail='ข้อมูลเซสชันไม่ถูกต้อง')
    throttle.clear(throttle_key)
    write_audit(
        db, user_id=session.user_id, action='aztek.connected', status='success',
        tool='aztek', resource_type='aztek_session', resource_id=session.user_id,
        request=request,
    )
    return {'status': 'connected', 'account_label': session.account_label}


@router.get('/api/aztek/status')
def aztek_status(request: Request, user: User = Depends(require_user),
                 db: Session = Depends(get_db)):
    return request.app.state.aztek_session_service.get_status(db, user)


@router.delete('/api/aztek/session', status_code=204)
def disconnect_aztek_session(request: Request, user: User = Depends(require_user),
                             db: Session = Depends(get_db)):
    removed = request.app.state.aztek_session_service.disconnect(db, user)
    if removed:
        write_audit(
            db, user_id=user.id, action='aztek.disconnected', status='success',
            tool='aztek', resource_type='aztek_session', resource_id=user.id,
            request=request,
        )
    return Response(status_code=204)


@router.get('/api/health')
def health():
    return {'ok': True}


@router.get('/api/games')
def games(user: User = Depends(require_user)):
    return {'games': list(item_finder.GAME_NAMES)}


@router.get('/api/modes')
def modes(user: User = Depends(require_user)):
    return {mode: item_service.mode_policy(mode)
            for mode in ('event', 'itemcode', 'shop')}


@router.get('/api/template')
def download_template(user: User = Depends(require_user)):
    handle, path = tempfile.mkstemp(suffix='.xlsx')
    os.close(handle)
    try:
        item_finder.download_template(path)
        with open(path, 'rb') as stream:
            content = stream.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return Response(
        content,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="item_finder_template.xlsx"'},
    )


@router.post('/api/import-template')
async def import_template(request: Request, file: UploadFile = File(...), mode: Mode = Form('event'),
                          workspace_id: str = Form(''),
                          user: User = Depends(require_user),
                          db: Session = Depends(get_db)):
    item_service.mode_policy(mode)
    path = await _temporary_upload(file)
    try:
        rows = await asyncio.to_thread(
            item_service.parse_workbook_locked, item_finder.read_template, path)
    except Exception as error:
        raise HTTPException(status_code=400, detail='อ่าน template ไม่สำเร็จ: %s' % error)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if workspace_id:
        repository = WorkspaceRepository(db)
        workspace = _get_workspace(repository, user.id, workspace_id)
        if workspace.mode != mode:
            raise HTTPException(status_code=400, detail='โหมดของงานไม่ตรงกับไฟล์ที่นำเข้า')
        workspace = repository.replace_template(
            user.id, workspace.id, file.filename or 'template.xlsx', rows)
    else:
        workspace = WorkspaceRepository(db).create(
            user.id, mode, file.filename or 'template.xlsx', rows)
    if not workspace_id:
        write_audit(
            db, user_id=user.id, action='workspace.created', status='success',
            summary={'mode': mode, 'filename': file.filename or 'template.xlsx'},
            tool='item_finder', resource_type='workspace',
            resource_id=workspace.id, request=request,
        )
    write_audit(
        db, user_id=user.id, action='template.imported', status='success',
        summary={
            'count': len(rows), 'mode': mode,
            'filename': file.filename or 'template.xlsx',
        },
        tool='item_finder', resource_type='workspace', resource_id=workspace.id,
        request=request,
    )
    return _workspace_view(workspace)


@router.post('/api/import-plan')
async def import_plan(request: Request, file: UploadFile = File(...), mode: Mode = Form('event'),
                      workspace_id: str = Form(''),
                      user: User = Depends(require_user),
                      db: Session = Depends(get_db)):
    parser = item_service.parser_for_mode(mode)
    repository = WorkspaceRepository(db)
    workspace = (_get_workspace(repository, user.id, workspace_id) if workspace_id
                 else repository.create(user.id, mode, file.filename or 'plan.xlsx'))
    if workspace.mode != mode:
        raise HTTPException(status_code=400, detail='โหมดของงานไม่ตรงกับไฟล์ที่นำเข้า')
    path = await _temporary_upload(file)
    try:
        sheets, skipped = await asyncio.to_thread(
            item_service.parse_workbook_locked, parser, path)
    except Exception as error:
        raise HTTPException(status_code=400, detail='อ่าน Event/Prize ไม่สำเร็จ: %s' % error)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if not sheets:
        raise HTTPException(status_code=400, detail='ไม่พบตารางไอเทมในไฟล์นี้')
    pending = repository.add_pending(user.id, workspace.id, sheets, skipped)
    if not workspace_id:
        write_audit(
            db, user_id=user.id, action='workspace.created', status='success',
            summary={'mode': mode, 'filename': file.filename or 'plan.xlsx'},
            tool='item_finder', resource_type='workspace',
            resource_id=workspace.id, request=request,
        )
    write_audit(
        db, user_id=user.id, action='plan.imported', status='success',
        summary={
            'count': sum(len(rows) for _name, rows in sheets), 'mode': mode,
            'filename': file.filename or 'plan.xlsx',
        },
        tool='item_finder', resource_type='workspace', resource_id=workspace.id,
        request=request,
    )
    return {
        'workspace_id': workspace.id,
        'pending_id': pending.id,
        'needs_sheet_selection': True,
        'sheets': [{'name': name, 'count': len(rows)} for name, rows in sheets],
        'skipped': list(skipped or []),
    }


@router.post('/api/import-plan/apply')
def apply_plan(payload: ApplyPlanRequest, request: Request,
               user: User = Depends(require_user),
               db: Session = Depends(get_db)):
    pending_id = payload.pending_id.strip()
    selected = payload.selected_sheets
    if not pending_id or not selected:
        raise HTTPException(status_code=400, detail='กรุณาเลือกอย่างน้อย 1 sheet')
    try:
        workspace = WorkspaceRepository(db).apply_pending(user.id, pending_id, selected)
    except (PendingImportNotFound, WorkspaceNotFound):
        raise HTTPException(status_code=404, detail='ไม่พบไฟล์นำเข้าที่รอเลือก sheet')
    write_audit(
        db, user_id=user.id, action='plan.applied', status='success',
        summary={'count': len(selected), 'mode': workspace.mode},
        tool='item_finder', resource_type='workspace', resource_id=workspace.id,
        request=request,
    )
    return _workspace_view(workspace)


@router.get('/api/workspaces/{workspace_id}')
def get_workspace(workspace_id: str, user: User = Depends(require_user),
                  db: Session = Depends(get_db)):
    return _workspace_view(
        _get_workspace(WorkspaceRepository(db), user.id, workspace_id))


@router.delete('/api/workspaces/{workspace_id}', status_code=204)
def delete_workspace(workspace_id: str, request: Request,
                     user: User = Depends(require_user),
                     db: Session = Depends(get_db)):
    repository = WorkspaceRepository(db)
    workspace = _get_workspace(repository, user.id, workspace_id)
    repository.delete_owned(user.id, workspace_id)
    write_audit(
        db, user_id=user.id, action='workspace.deleted', status='success',
        summary={'mode': workspace.mode, 'filename': workspace.filename},
        tool='item_finder', resource_type='workspace', resource_id=workspace_id,
        request=request,
    )
    return Response(status_code=204)


@router.get('/api/workspaces/{workspace_id}/export.csv')
def export_csv(workspace_id: str, request: Request,
               user: User = Depends(require_user),
               db: Session = Depends(get_db)):
    workspace = _get_workspace(WorkspaceRepository(db), user.id, workspace_id)
    if not workspace.results:
        raise HTTPException(status_code=400, detail='ยังไม่มีผลลัพธ์')
    write_audit(
        db, user_id=user.id, action='workspace.exported_csv', status='success',
        summary={
            'count': len(workspace.results), 'format': 'csv', 'game': workspace.game,
        },
        tool='item_finder', resource_type='workspace', resource_id=workspace_id,
        request=request,
    )
    return Response(
        item_service.export_csv_bytes(workspace.results),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="item_finder_results.csv"'},
    )


@router.get('/api/workspaces/{workspace_id}/export.xlsx')
def export_xlsx(workspace_id: str, request: Request,
                user: User = Depends(require_user),
                db: Session = Depends(get_db)):
    workspace = _get_workspace(WorkspaceRepository(db), user.id, workspace_id)
    if not workspace.results:
        raise HTTPException(status_code=400, detail='ยังไม่มีผลลัพธ์')
    write_audit(
        db, user_id=user.id, action='workspace.exported_xlsx', status='success',
        summary={
            'count': len(workspace.results), 'format': 'xlsx', 'game': workspace.game,
        },
        tool='item_finder', resource_type='workspace', resource_id=workspace_id,
        request=request,
    )
    return Response(
        item_service.export_xlsx_bytes(workspace.results, workspace.game),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="item_finder_results.xlsx"'},
    )


@router.post('/api/workspaces/{workspace_id}/bundles')
def bundle_preview(workspace_id: str, payload: BundleRequest, request: Request,
                   user: User = Depends(require_user), db: Session = Depends(get_db)):
    workspace = _get_workspace(WorkspaceRepository(db), user.id, workspace_id)
    indexes = payload.selected_indexes
    if indexes:
        rows = [workspace.results[index] for index in sorted(set(indexes))
                if isinstance(index, int) and 0 <= index < len(workspace.results)]
    else:
        rows = workspace.results
    if not rows:
        raise HTTPException(status_code=400, detail='ไม่มีไอเทมให้รวมเป็นบันเดิล')
    bundles = item_service.build_bundles(rows, workspace.group_meta)
    write_audit(
        db, user_id=user.id, action='bundle.previewed', status='success',
        summary={'count': len(rows), 'mode': workspace.mode},
        tool='item_finder', resource_type='workspace', resource_id=workspace_id,
        request=request,
    )
    return {'bundles': bundles}


@router.websocket('/ws/search')
async def ws_search(ws: WebSocket):
    """Run the existing Item Finder engine headlessly and stream events."""
    application = ws.scope['app']
    raw_session = ws.cookies.get('afc_session', '')
    with application.state.database.session() as db:
        user = application.state.auth_service.resolve_session(db, raw_session)
    if user is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    try:
        request = await ws.receive_json()
    except Exception:
        await ws.close()
        return

    workspace_id = str(request.get('workspace_id') or '')
    with application.state.database.session() as db:
        repository = WorkspaceRepository(db)
        try:
            workspace = repository.get_owned(user.id, workspace_id)
        except WorkspaceNotFound:
            await ws.close(code=4404)
            return
        # A new search invalidates the previous result set even if validation,
        # browser launch, or Playwright later fails.
        repository.save_results(
            user.id, workspace_id, game=workspace.game or '', results=[], not_found=[])
    game = request.get('game') or ''
    web_mode = request.get('web_mode') or item_service.mode_policy(workspace.mode)['web_mode']

    async def send(message):
        await ws.send_json(message)

    try:
        data = search_runner.build_search_data(
            game, workspace.criteria, web_mode, mode=workspace.mode)
    except Exception as error:
        await send({'type': 'log', 'msg': str(error), 'level': 'ERROR'})
        await send({'type': 'done', 'count': 0, 'not_found': []})
        await ws.close()
        return

    queue = asyncio.Queue()
    finder = search_runner.HeadlessFinder(
        lambda msg, level='INFO': queue.put_nowait(
            {'type': 'log', 'msg': msg, 'level': level}),
        lambda item: queue.put_nowait(
            {'type': 'result', 'item': search_runner.result_view(item)}),
        lambda current, total, name: queue.put_nowait(
            {'type': 'progress', 'cur': current, 'total': total, 'name': name}),
        occurrences=workspace.occurrences,
        on_reset=lambda: queue.put_nowait({'type': 'reset_results'}),
    )

    async def run_search():
        try:
            await finder._auto(data)
            results = [dict(row) for row in finder._results]
            not_found = list(finder._not_found)
            with application.state.database.session() as db:
                WorkspaceRepository(db).save_results(
                    user.id, workspace_id, game=game, results=results,
                    not_found=not_found)
            queue.put_nowait({'type': 'done', 'count': len(results),
                              'not_found': not_found})
        except core.BrowserBusy as error:
            queue.put_nowait({'type': 'log', 'msg': str(error), 'level': 'ERROR'})
            queue.put_nowait({'type': 'done', 'count': 0, 'not_found': []})
        except Exception as error:
            queue.put_nowait({'type': 'log', 'msg': 'error: %s' % error, 'level': 'ERROR'})
            queue.put_nowait({'type': 'done', 'count': 0, 'not_found': []})
        finally:
            queue.put_nowait(None)

    task = asyncio.create_task(run_search())
    try:
        while True:
            message = await queue.get()
            if message is None:
                break
            await send(message)
    except WebSocketDisconnect:
        finder._cancel = True
    finally:
        await task
        try:
            await ws.close()
        except Exception:
            pass


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_database = database or Database(resolved_settings)
    auth_service = AuthService(resolved_settings)
    aztek_session_service = AztekSessionService(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        with application.state.database.session() as db:
            application.state.auth_service.bootstrap_admin(db)
        yield

    application = FastAPI(title='All for Cabal — Web', lifespan=lifespan)
    application.state.settings = resolved_settings
    application.state.database = resolved_database
    application.state.auth_service = auth_service
    application.state.aztek_session_service = aztek_session_service
    application.state.login_throttle = LoginThrottle(monotonic_clock)
    application.state.pairing_throttle = LoginThrottle(monotonic_clock)
    application.include_router(router)
    return application


app = create_app()
