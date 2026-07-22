# -*- coding: utf-8 -*-
"""All for Cabal Web — local Item Finder application."""
import asyncio
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
from web.auth_service import AuthService  # noqa: E402
from web.db import Database  # noqa: E402
from web.models import User, utc_now  # noqa: E402
from web.security import hash_password, verify_password  # noqa: E402
from web.settings import Settings  # noqa: E402


router = APIRouter()
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
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


def _get_workspace(workspace_id):
    try:
        return WORKSPACES.get(workspace_id)
    except KeyError:
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


@router.post('/api/auth/login')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else 'unknown'
    throttle: LoginThrottle = request.app.state.login_throttle
    if throttle.is_limited(client_ip):
        raise HTTPException(status_code=429, detail='ลองใหม่ภายหลัง')
    user = request.app.state.auth_service.authenticate(
        db, payload.username, payload.password
    )
    if user is None:
        throttle.record_failure(client_ip)
        raise HTTPException(
            status_code=401, detail='ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
        )
    throttle.clear(client_ip)
    response = JSONResponse(_safe_user(user))
    _set_session_cookie(
        response,
        request.app.state.auth_service.create_session(db, user),
        request.app.state.settings,
    )
    return response


@router.post('/api/auth/logout', status_code=204)
def logout(
    request: Request,
    afc_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    request.app.state.auth_service.revoke_session(db, afc_session)
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


@router.get('/api/health')
def health():
    return {'ok': True}


@router.get('/api/games')
def games():
    return {'games': list(item_finder.GAME_NAMES)}


@router.get('/api/modes')
def modes():
    return {mode: item_service.mode_policy(mode)
            for mode in ('event', 'itemcode', 'shop')}


@router.get('/api/template')
def download_template():
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
async def import_template(file: UploadFile = File(...), mode: Mode = Form('event'),
                          workspace_id: str = Form('')):
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
        workspace = _get_workspace(workspace_id)
        if workspace.mode != mode:
            raise HTTPException(status_code=400, detail='โหมดของงานไม่ตรงกับไฟล์ที่นำเข้า')
        workspace = WORKSPACES.replace_template(
            workspace.id, file.filename or 'template.xlsx', rows)
    else:
        workspace = WORKSPACES.create(mode, file.filename or 'template.xlsx', rows)
    return _workspace_view(workspace)


@router.post('/api/import-plan')
async def import_plan(file: UploadFile = File(...), mode: Mode = Form('event'),
                      workspace_id: str = Form('')):
    parser = item_service.parser_for_mode(mode)
    workspace = (_get_workspace(workspace_id) if workspace_id
                 else WORKSPACES.create(mode, file.filename or 'plan.xlsx'))
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
    pending = WORKSPACES.add_pending(workspace.id, sheets, skipped)
    return {
        'workspace_id': workspace.id,
        'pending_id': pending.id,
        'needs_sheet_selection': True,
        'sheets': [{'name': name, 'count': len(rows)} for name, rows in sheets],
        'skipped': list(skipped or []),
    }


@router.post('/api/import-plan/apply')
def apply_plan(payload: ApplyPlanRequest):
    pending_id = payload.pending_id.strip()
    selected = payload.selected_sheets
    if not pending_id or not selected:
        raise HTTPException(status_code=400, detail='กรุณาเลือกอย่างน้อย 1 sheet')
    try:
        workspace = WORKSPACES.apply_pending(pending_id, selected)
    except KeyError:
        raise HTTPException(status_code=404, detail='ไม่พบไฟล์นำเข้าที่รอเลือก sheet')
    return _workspace_view(workspace)


@router.get('/api/workspaces/{workspace_id}')
def get_workspace(workspace_id: str):
    return _workspace_view(_get_workspace(workspace_id))


@router.delete('/api/workspaces/{workspace_id}', status_code=204)
def delete_workspace(workspace_id: str):
    _get_workspace(workspace_id)
    WORKSPACES.delete(workspace_id)
    return Response(status_code=204)


@router.get('/api/workspaces/{workspace_id}/export.csv')
def export_csv(workspace_id: str):
    workspace = _get_workspace(workspace_id)
    if not workspace.results:
        raise HTTPException(status_code=400, detail='ยังไม่มีผลลัพธ์')
    return Response(
        item_service.export_csv_bytes(workspace.results),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="item_finder_results.csv"'},
    )


@router.get('/api/workspaces/{workspace_id}/export.xlsx')
def export_xlsx(workspace_id: str):
    workspace = _get_workspace(workspace_id)
    if not workspace.results:
        raise HTTPException(status_code=400, detail='ยังไม่มีผลลัพธ์')
    return Response(
        item_service.export_xlsx_bytes(workspace.results, workspace.game),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="item_finder_results.xlsx"'},
    )


@router.post('/api/workspaces/{workspace_id}/bundles')
def bundle_preview(workspace_id: str, payload: BundleRequest):
    workspace = _get_workspace(workspace_id)
    indexes = payload.selected_indexes
    if indexes:
        rows = [workspace.results[index] for index in sorted(set(indexes))
                if isinstance(index, int) and 0 <= index < len(workspace.results)]
    else:
        rows = workspace.results
    if not rows:
        raise HTTPException(status_code=400, detail='ไม่มีไอเทมให้รวมเป็นบันเดิล')
    return {'bundles': item_service.build_bundles(rows, workspace.group_meta)}


@router.websocket('/ws/search')
async def ws_search(ws: WebSocket):
    """Run the existing Item Finder engine headlessly and stream events."""
    await ws.accept()
    try:
        request = await ws.receive_json()
    except Exception:
        await ws.close()
        return

    workspace_id = str(request.get('workspace_id') or '')
    try:
        workspace = _get_workspace(workspace_id)
    except HTTPException as error:
        await ws.send_json({'type': 'log', 'msg': error.detail, 'level': 'ERROR'})
        await ws.send_json({'type': 'done', 'count': 0, 'not_found': []})
        await ws.close()
        return
    # A new search invalidates the previous result set even if validation,
    # browser launch, or Playwright later fails.
    workspace.results = []
    workspace.not_found = []
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
            workspace.results = [dict(row) for row in finder._results]
            workspace.not_found = list(finder._not_found)
            workspace.game = game
            queue.put_nowait({'type': 'done', 'count': len(workspace.results),
                              'not_found': workspace.not_found})
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

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        with application.state.database.session() as db:
            application.state.auth_service.bootstrap_admin(db)
        yield

    application = FastAPI(title='All for Cabal — Web', lifespan=lifespan)
    application.state.settings = resolved_settings
    application.state.database = resolved_database
    application.state.auth_service = auth_service
    application.state.login_throttle = LoginThrottle(monotonic_clock)
    application.include_router(router)
    return application


app = create_app()
