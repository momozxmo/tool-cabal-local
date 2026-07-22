# -*- coding: utf-8 -*-
"""Authenticated API-level tests for Item Finder web parity endpoints."""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import item_finder  # noqa: E402
from web import item_service, search_runner  # noqa: E402
from web.models import WorkspaceRecord  # noqa: E402
from web.workspaces import WorkspaceRepository  # noqa: E402


def make_template_bytes():
    handle, path = tempfile.mkstemp(suffix='.xlsx')
    os.close(handle)
    try:
        item_finder.download_template(path)
        with open(path, 'rb') as stream:
            return stream.read()
    finally:
        os.unlink(path)


def test_modes_and_template_download(client):
    response = client.get('/api/modes')
    assert response.status_code == 200
    assert set(response.json()) == {'event', 'itemcode', 'shop'}
    assert response.json()['itemcode']['web_locked'] is True
    response = client.get('/api/template')
    assert response.status_code == 200
    assert response.content[:2] == b'PK'
    assert 'attachment' in response.headers['content-disposition']


def test_import_template_creates_workspace_and_clear_deletes_it(client):
    response = client.post(
        '/api/import-template', data={'mode': 'event'},
        files={'file': (
            'template.xlsx', make_template_bytes(),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['workspace_id']
    assert body['mode'] == 'event'
    assert body['count'] == 2
    assert len(body['items']) == 2
    workspace_id = body['workspace_id']
    assert client.get('/api/workspaces/' + workspace_id).status_code == 200
    assert client.delete('/api/workspaces/' + workspace_id).status_code == 204
    assert client.get('/api/workspaces/' + workspace_id).status_code == 404


def test_plan_import_returns_sheet_picker_then_applies_selected_sheets(client, monkeypatch):
    monkeypatch.setattr(item_service, 'parser_for_mode', lambda mode: (
        lambda path: ([
            ('One', [{'kind': '1', 'sources': ['G1']}]),
            ('Two', [{'kind': '2', 'sources': ['G2']}]),
        ], ['Skipped'])
    ))
    response = client.post(
        '/api/import-plan', data={'mode': 'shop'},
        files={'file': ('plan.xlsx', b'fake workbook', 'application/octet-stream')},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['needs_sheet_selection'] is True
    assert [sheet['name'] for sheet in body['sheets']] == ['One', 'Two']
    response = client.post('/api/import-plan/apply', json={
        'pending_id': body['pending_id'], 'selected_sheets': ['Two'],
    })
    assert response.status_code == 200, response.text
    applied = response.json()
    assert applied['mode'] == 'shop'
    assert [row['kind'] for row in applied['items']] == ['2']
    assert applied['skipped'] == ['Skipped']


def test_workspace_results_export_and_bundle_preview(client, member, test_database):
    with test_database.session() as db:
        workspace = WorkspaceRepository(db).create(member.id, 'event', 'plan.xlsx')
        workspace.game = 'CabalM SEA'
        workspace.group_meta = {
            'G1': {'activity': 'Event A'}, 'G2': {'activity': 'Event A'},
        }
        workspace.results = [
            {'aztek_id': '99', 'item_name': 'Shared', 'item_kind': '1',
             'sources': ['G1']},
            {'aztek_id': '11', 'item_name': 'Only 1', 'item_kind': '2',
             'sources': ['G1']},
            {'aztek_id': '99', 'item_name': 'Shared', 'item_kind': '1',
             'sources': ['G2']},
            {'aztek_id': '22', 'item_name': 'Only 2', 'item_kind': '3',
             'sources': ['G2']},
        ]
        workspace.not_found = [['#5 Kind=404', 'missing row']]
        workspace_id = workspace.id

    response = client.get(f'/api/workspaces/{workspace_id}')
    assert response.status_code == 200
    assert response.json()['result_count'] == 4
    assert len(response.json()['results']) == 4
    assert response.json()['not_found'][0][0].startswith('#5')

    response = client.get(f'/api/workspaces/{workspace_id}/export.csv')
    assert response.status_code == 200
    assert response.content.startswith(b'\xef\xbb\xbf')
    response = client.get(f'/api/workspaces/{workspace_id}/export.xlsx')
    assert response.status_code == 200
    assert response.content[:2] == b'PK'

    response = client.post(
        f'/api/workspaces/{workspace_id}/bundles',
        json={'selected_indexes': [0, 1, 2, 3]},
    )
    assert response.status_code == 200, response.text
    bundles = response.json()['bundles']
    assert [bundle['name'] for bundle in bundles] == ['Event A - G1', 'Event A - G2']
    assert [[item['id'] for item in bundle['items']] for bundle in bundles] == [
        ['11', '99'], ['22', '99'],
    ]


def test_search_websocket_persists_results_not_found_and_regroups(
    client, member, test_database, monkeypatch
):
    with test_database.session() as db:
        workspace = WorkspaceRepository(db).create(member.id, 'event', 'plan.xlsx')
        workspace.criteria = [{'kind': '1', 'opt': '', 'dur': '', 'name': 'A'}]
        workspace.occurrences = [
            {'kind': '1', 'opt': '', 'dur': '', 'name': 'A file', 'sources': ['G1']},
            {'kind': '1', 'opt': '', 'dur': '', 'name': 'A file', 'sources': ['G2']},
        ]
        workspace_id = workspace.id

    async def fake_auto(finder, data):
        row = {
            'aztek_id': '10', 'item_name': 'A web', 'item_kind': '1',
            'item_option': '', 'duration_index': '', 'game': data['game'],
        }
        finder._results = [row]
        finder.add_result_row(row)
        finder._not_found = [['#2 Kind=404', 'missing row']]
        finder._regroup_results()

    monkeypatch.setattr(search_runner.HeadlessFinder, '_auto', fake_auto)
    messages = []
    with client.websocket_connect('/ws/search') as websocket:
        websocket.send_json({
            'workspace_id': workspace_id, 'game': 'CabalM SEA', 'web_mode': 'any',
        })
        while True:
            message = websocket.receive_json()
            messages.append(message)
            if message['type'] == 'done':
                break

    assert [message['type'] for message in messages].count('reset_results') == 1
    assert [message['type'] for message in messages].count('result') == 3
    done = messages[-1]
    assert done['count'] == 2
    assert done['not_found'][0][0].startswith('#2')
    with test_database.session() as db:
        saved = db.get(WorkspaceRecord, workspace_id)
        assert saved is not None
        assert [row['sources'] for row in saved.results] == [['G1'], ['G2']]


def test_failed_search_clears_previous_workspace_results(client, member, test_database):
    with test_database.session() as db:
        workspace = WorkspaceRepository(db).create(
            member.id, 'event', 'template.xlsx', [{'kind': '1'}]
        )
        workspace.results = [{'aztek_id': 'OLD'}]
        workspace.not_found = [['old', 'old']]
        workspace_id = workspace.id

    with client.websocket_connect('/ws/search') as websocket:
        websocket.send_json({
            'workspace_id': workspace_id, 'game': 'INVALID GAME', 'web_mode': 'any',
        })
        while True:
            message = websocket.receive_json()
            if message['type'] == 'done':
                break

    with test_database.session() as db:
        saved = db.get(WorkspaceRecord, workspace_id)
        assert saved is not None
        assert saved.results == []
        assert saved.not_found == []


def test_invalid_mode_and_bundle_indexes_are_rejected_not_server_errors(
    client, member, test_database
):
    response = client.post(
        '/api/import-template', data={'mode': 'invalid'},
        files={'file': ('template.xlsx', make_template_bytes(), 'application/octet-stream')},
    )
    assert response.status_code in (400, 422)
    with test_database.session() as db:
        workspace = WorkspaceRepository(db).create(member.id, 'event')
        workspace.results = [{'aztek_id': '1', 'item_name': 'A'}]
        workspace_id = workspace.id
    response = client.post(
        f'/api/workspaces/{workspace_id}/bundles',
        json={'selected_indexes': [0, 'bad']},
    )
    assert response.status_code in (400, 422)
