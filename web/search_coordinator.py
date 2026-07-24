# -*- coding: utf-8 -*-
"""Per-user search lifecycle: concurrency gate, persisted jobs, session expiry.

The coordinator is the only place that turns a decrypted Aztek storage state
into a running search. It bounds concurrency with a semaphore, records each run
as a ``Job`` row, streams engine events to the caller, and — critically — never
lets ciphertext or another user's session reach the browser.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import aztek_core as core

from web import search_runner
from web.audit import write_audit
from web.models import Job, User, utc_now
from web.security import InvalidEncryptedState
from web.workspaces import WorkspaceNotFound, WorkspaceRepository


_MAX_LOG_LINES = 500


Emit = Callable[[dict], Awaitable[None]]


class SearchCoordinator:
    def __init__(self, database, settings, aztek_session_service) -> None:
        self._database = database
        self._settings = settings
        self._aztek = aztek_session_service
        self._semaphore = asyncio.Semaphore(max(1, settings.browser_concurrency))

    async def run(self, user_id: str, workspace_id: str,
                  request_data: dict, emit: Emit) -> None:
        game = str(request_data.get('game') or '')
        web_mode = request_data.get('web_mode')

        # 1. Load owned workspace, snapshot its data, and decrypt the session.
        with self._database.session() as db:
            repository = WorkspaceRepository(db)
            try:
                workspace = repository.get_owned(user_id, workspace_id)
            except WorkspaceNotFound:
                await emit({'type': 'error', 'code': 'workspace_not_found',
                            'msg': 'ไม่พบงาน Item Finder นี้'})
                return
            mode = workspace.mode
            criteria = list(workspace.criteria)
            occurrences = list(workspace.occurrences)
            if not web_mode:
                web_mode = None
            user = db.get(User, user_id)
            try:
                storage_state = self._aztek.load_storage_state(db, user)
            except InvalidEncryptedState:
                storage_state = None

        # 2. A connected Aztek session is required before any browser launch.
        if storage_state is None:
            await emit({'type': 'error', 'code': 'aztek_session_required',
                        'msg': 'ยังไม่ได้เชื่อมเซสชัน Aztek — ไปที่หน้า /account'})
            await emit({'type': 'done', 'count': 0, 'not_found': []})
            return

        # 3. Starting a search invalidates prior results even if it later fails.
        with self._database.session() as db:
            WorkspaceRepository(db).save_results(
                user_id, workspace_id, game=game, results=[], not_found=[])

        # 4. Validate the search request before creating a job.
        try:
            data = search_runner.build_search_data(
                game, criteria, web_mode, mode=mode)
        except Exception as error:
            await emit({'type': 'log', 'msg': str(error), 'level': 'ERROR'})
            await emit({'type': 'done', 'count': 0, 'not_found': []})
            return

        # 5. Persist a queued job, then run under the concurrency gate.
        with self._database.session() as db:
            job = Job(owner_user_id=user_id, workspace_id=workspace_id,
                      tool='item_finder', status='queued',
                      config={'game': game, 'mode': mode, 'web_mode': web_mode or ''})
            db.add(job)
            db.flush()
            job_id = job.id
        await emit({'type': 'job', 'job_id': job_id, 'status': 'queued'})

        await self._run_job(user_id, workspace_id, job_id, game, data,
                            occurrences, storage_state, emit)

    async def _run_job(self, user_id, workspace_id, job_id, game, data,
                       occurrences, storage_state, emit) -> None:
        queue: asyncio.Queue = asyncio.Queue()
        finder = search_runner.HeadlessFinder(
            lambda msg, level='INFO': queue.put_nowait(
                {'type': 'log', 'msg': msg, 'level': level}),
            lambda item: queue.put_nowait(
                {'type': 'result', 'item': search_runner.result_view(item)}),
            lambda cur, total, name: queue.put_nowait(
                {'type': 'progress', 'cur': cur, 'total': total, 'name': name}),
            occurrences=occurrences,
            on_reset=lambda: queue.put_nowait({'type': 'reset_results'}),
        )

        log_lines: list[str] = []
        outcome = {'status': 'failed', 'code': None, 'reason': None,
                   'results': [], 'not_found': []}

        async def run_search():
            await self._semaphore.acquire()
            try:
                queue.put_nowait({'type': 'job', 'job_id': job_id, 'status': 'running'})
                self._mark_job_running(job_id)
                await finder.run(data, storage_state)
                # Persist the same view that was streamed to the browser so a
                # workspace reload keeps every derived field (params, groups, and
                # the name_mismatch highlight flag).
                outcome['results'] = [
                    search_runner.result_view(row) for row in finder._results]
                outcome['not_found'] = list(finder._not_found)
                outcome['status'] = 'cancelled' if finder._cancel else 'done'
                queue.put_nowait({'type': 'done', 'count': len(outcome['results']),
                                  'not_found': outcome['not_found']})
            except search_runner.AztekSessionExpired as error:
                outcome['code'] = 'aztek_session_expired'
                outcome['reason'] = str(error)
                queue.put_nowait({'type': 'error', 'code': 'aztek_session_expired',
                                  'msg': str(error)})
                queue.put_nowait({'type': 'done', 'count': 0, 'not_found': []})
            except core.BrowserBusy as error:
                outcome['code'] = 'browser_busy'
                outcome['reason'] = str(error)
                queue.put_nowait({'type': 'log', 'msg': str(error), 'level': 'ERROR'})
                queue.put_nowait({'type': 'done', 'count': 0, 'not_found': []})
            except Exception as error:  # noqa: BLE001 - surface as a failed job
                outcome['code'] = 'error'
                outcome['reason'] = str(error)
                queue.put_nowait({'type': 'log', 'msg': 'error: %s' % error,
                                  'level': 'ERROR'})
                queue.put_nowait({'type': 'done', 'count': 0, 'not_found': []})
            finally:
                self._semaphore.release()
                queue.put_nowait(None)

        task = asyncio.create_task(run_search())
        client_gone = False
        while True:
            message = await queue.get()
            if message is None:
                break
            if message.get('type') == 'log' and len(log_lines) < _MAX_LOG_LINES:
                log_lines.append('%s: %s' % (
                    message.get('level', 'INFO'), message.get('msg', '')))
            if not client_gone:
                try:
                    await emit(message)
                except Exception:  # noqa: BLE001 - client vanished mid-stream
                    client_gone = True
                    finder._cancel = True
        await task
        self._finalize(user_id, workspace_id, job_id, game, outcome, log_lines)

    def _mark_job_running(self, job_id: str) -> None:
        with self._database.session() as db:
            job = db.get(Job, job_id)
            if job is not None:
                job.status = 'running'
                job.started_at = utc_now()

    def _finalize(self, user_id, workspace_id, job_id, game, outcome,
                  log_lines) -> None:
        status = outcome['status']
        with self._database.session() as db:
            job = db.get(Job, job_id)
            if job is not None:
                job.status = status
                job.finished_at = utc_now()
                job.log = log_lines
                job.result = {
                    'count': len(outcome['results']),
                    'not_found': outcome['not_found'],
                    'code': outcome['code'],
                    'reason': outcome['reason'],
                }

            if status in ('done', 'cancelled'):
                WorkspaceRepository(db).save_results(
                    user_id, workspace_id, game=game,
                    results=outcome['results'], not_found=outcome['not_found'])
                user = db.get(User, user_id)
                session = self._aztek_session_for(db, user)
                if session is not None:
                    session.last_validated_at = utc_now()
                if status == 'done':
                    write_audit(
                        db, user_id=user_id, action='item_finder.completed',
                        status='success',
                        summary={'count': len(outcome['results']), 'game': game},
                        tool='item_finder', resource_type='workspace',
                        resource_id=workspace_id)
            else:
                if outcome['code'] == 'aztek_session_expired':
                    user = db.get(User, user_id)
                    self._aztek.mark_expired(db, user)
                    write_audit(
                        db, user_id=user_id, action='aztek.expired',
                        status='failure', tool='aztek',
                        resource_type='aztek_session', resource_id=user_id)
                write_audit(
                    db, user_id=user_id, action='item_finder.failed',
                    status='failure',
                    summary={'game': game, 'reason': outcome['code'] or 'error'},
                    tool='item_finder', resource_type='workspace',
                    resource_id=workspace_id)

    def _aztek_session_for(self, db, user):
        if user is None:
            return None
        # Reuse the service's lookup shape without exposing ciphertext.
        from sqlalchemy import select

        from web.models import AztekSession
        return db.scalar(
            select(AztekSession).where(AztekSession.user_id == user.id))
