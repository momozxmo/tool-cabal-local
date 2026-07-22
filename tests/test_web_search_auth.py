from __future__ import annotations

from sqlalchemy import select

import item_finder
from web import search_runner
from web.models import Job


def _connect_aztek(client, anonymous_client):
    token = client.post('/api/aztek/pairing-token').json()['pairing_token']
    response = anonymous_client.post('/api/aztek/pair', json={
        'pairing_token': token,
        'account_label': 'test',
        'storage_state': {
            'cookies': [{
                'name': 'session', 'value': 'cookie-value',
                'domain': '.combo-interactive.com', 'path': '/',
            }],
            'origins': [],
        },
    })
    assert response.status_code == 200


def _drain(ws) -> list[dict]:
    messages = []
    while True:
        message = ws.receive_json()
        messages.append(message)
        if message.get('type') == 'done':
            return messages


def test_search_requires_connected_aztek_session(client, workspace_for_member):
    with client.websocket_connect('/ws/search') as ws:
        ws.send_json({'workspace_id': workspace_for_member.id,
                      'game': item_finder.GAME_NAMES[0]})
        first = ws.receive_json()
    assert first['code'] == 'aztek_session_required'


def test_expired_session_marks_status_and_fails_the_job(
        client, anonymous_client, member, workspace_for_member,
        test_database, monkeypatch):
    _connect_aztek(client, anonymous_client)

    async def boom(self, data, storage_state):
        raise search_runner.AztekSessionExpired('Aztek session หมดอายุ')

    monkeypatch.setattr(search_runner.HeadlessFinder, 'run', boom)

    with client.websocket_connect('/ws/search') as ws:
        ws.send_json({'workspace_id': workspace_for_member.id,
                      'game': item_finder.GAME_NAMES[0]})
        messages = _drain(ws)

    assert any(m.get('code') == 'aztek_session_expired' for m in messages)
    assert client.get('/api/aztek/status').json()['status'] == 'expired'
    with test_database.session() as db:
        job = db.scalar(select(Job).where(Job.owner_user_id == member.id))
        assert job is not None
        assert job.status == 'failed'
        assert job.result['code'] == 'aztek_session_expired'


def test_successful_search_persists_results_and_completes_job(
        client, anonymous_client, member, workspace_for_member,
        test_database, monkeypatch):
    _connect_aztek(client, anonymous_client)

    async def fake_run(self, data, storage_state):
        self._results = [{
            'aztek_id': '221070', 'item_name': 'Force Wing',
            'sources': ['Cash Shop']}]
        self._not_found = []

    monkeypatch.setattr(search_runner.HeadlessFinder, 'run', fake_run)

    with client.websocket_connect('/ws/search') as ws:
        ws.send_json({'workspace_id': workspace_for_member.id,
                      'game': item_finder.GAME_NAMES[0]})
        messages = _drain(ws)

    done = [m for m in messages if m.get('type') == 'done'][-1]
    assert done['count'] == 1

    view = client.get('/api/workspaces/%s' % workspace_for_member.id).json()
    assert view['result_count'] == 1
    assert client.get('/api/aztek/status').json()['status'] == 'active'
    with test_database.session() as db:
        job = db.scalar(select(Job).where(Job.owner_user_id == member.id))
        assert job is not None
        assert job.status == 'done'
        assert job.result['count'] == 1


def test_search_rejects_foreign_workspace_over_websocket(
        client_for, other_member, workspace_for_member):
    outsider = client_for(other_member)
    with outsider.websocket_connect('/ws/search') as ws:
        ws.send_json({'workspace_id': workspace_for_member.id,
                      'game': item_finder.GAME_NAMES[0]})
        # Server closes with 4404 before sending any application message.
        import pytest
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect) as error:
            ws.receive_json()
    assert error.value.code == 4404
