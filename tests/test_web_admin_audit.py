import json
from types import SimpleNamespace

from sqlalchemy import select

from web.audit import write_audit
from web.models import AuditLog
from web.workspaces import WorkspaceRepository


def _audit_rows(db):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at)).all()


def test_write_audit_keeps_only_allowlisted_scalar_summary_and_request_metadata(
    db_session,
):
    request = SimpleNamespace(
        client=SimpleNamespace(host='9' * 300),
        headers={
            'user-agent': 'browser/' + ('x' * 600),
            'authorization': 'Bearer do-not-store',
            'cookie': 'afc_session=do-not-store',
        },
    )

    write_audit(
        db_session,
        user_id=None,
        action='test.sanitized',
        status='success',
        summary={
            'mode': 'event',
            'count': 3,
            'password': 'do-not-store',
            'token_hint': 'do-not-store',
            'nested': {'not': 'scalar'},
            'reason': ['not', 'scalar'],
        },
        request=request,
    )
    db_session.flush()

    row = _audit_rows(db_session)[0]
    assert json.loads(row.summary) == {'count': 3, 'mode': 'event'}
    assert len(row.ip_address) == 255
    assert len(row.user_agent) == 512
    assert 'do-not-store' not in row.summary
    assert 'do-not-store' not in row.user_agent


def test_write_audit_truncates_summary_as_valid_json_within_storage_limit(db_session):
    write_audit(
        db_session,
        user_id=None,
        action='test.truncated',
        status='success',
        summary={'filename': 'x' * 10000, 'reason': 'y' * 10000},
    )
    db_session.flush()

    summary = _audit_rows(db_session)[0].summary
    assert len(summary) <= 2000
    assert isinstance(json.loads(summary), dict)


def test_write_audit_truncation_is_deterministic_across_summary_key_order(db_session):
    write_audit(
        db_session,
        user_id=None,
        action='test.deterministic-first',
        status='success',
        summary={'filename': 'f' * 2000, 'reason': 'r' * 2000},
    )
    write_audit(
        db_session,
        user_id=None,
        action='test.deterministic-second',
        status='success',
        summary={'reason': 'r' * 2000, 'filename': 'f' * 2000},
    )
    db_session.flush()

    first, second = _audit_rows(db_session)
    assert first.summary == second.summary


def test_write_audit_uses_the_callers_transaction(db_session):
    write_audit(
        db_session, user_id=None, action='test.transaction', status='success'
    )
    db_session.rollback()

    assert _audit_rows(db_session) == []


def test_workspace_import_export_and_bundle_actions_are_audited(
    client, member, test_database, monkeypatch
):
    import item_finder
    from web import item_service

    monkeypatch.setattr(item_finder, 'read_template', lambda _path: [
        {'kind': '1', 'opt': '', 'dur': '', 'name': 'Item'},
    ])
    imported = client.post(
        '/api/import-template',
        data={'mode': 'event'},
        files={'file': ('template.xlsx', b'workbook', 'application/octet-stream')},
    )
    assert imported.status_code == 200, imported.text
    imported_workspace_id = imported.json()['workspace_id']
    assert client.delete('/api/workspaces/' + imported_workspace_id).status_code == 204

    monkeypatch.setattr(item_service, 'parser_for_mode', lambda _mode: (
        lambda _path: ([('One', [{'kind': '1', 'sources': ['G1']}])], [])
    ))
    pending = client.post(
        '/api/import-plan',
        data={'mode': 'shop'},
        files={'file': ('plan.xlsx', b'workbook', 'application/octet-stream')},
    )
    assert pending.status_code == 200, pending.text
    applied = client.post('/api/import-plan/apply', json={
        'pending_id': pending.json()['pending_id'], 'selected_sheets': ['One'],
    })
    assert applied.status_code == 200, applied.text

    with test_database.session() as db:
        workspace = WorkspaceRepository(db).create(member.id, 'event', 'results.xlsx')
        workspace.game = 'CabalM SEA'
        workspace.results = [{'aztek_id': '1', 'item_name': 'Item', 'sources': ['G1']}]
        workspace.group_meta = {'G1': {'activity': 'Event'}}
        result_workspace_id = workspace.id

    assert client.get(f'/api/workspaces/{result_workspace_id}/export.csv').status_code == 200
    assert client.get(f'/api/workspaces/{result_workspace_id}/export.xlsx').status_code == 200
    assert client.post(
        f'/api/workspaces/{result_workspace_id}/bundles',
        json={'selected_indexes': [0]},
    ).status_code == 200

    with test_database.session() as db:
        actions = {row.action for row in _audit_rows(db)}
    assert {
        'workspace.created',
        'workspace.deleted',
        'template.imported',
        'plan.imported',
        'plan.applied',
        'workspace.exported_csv',
        'workspace.exported_xlsx',
        'bundle.previewed',
    } <= actions
