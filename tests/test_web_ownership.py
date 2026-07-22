import pytest

from web.models import User
from web.workspaces import PendingImportNotFound, WorkspaceNotFound, WorkspaceRepository


@pytest.fixture
def member(db_session):
    user = User(username='workspace.member', password_hash='hash')
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def other_member(db_session):
    user = User(username='workspace.other', password_hash='hash')
    db_session.add(user)
    db_session.flush()
    return user


def test_workspace_repository_scopes_every_workspace_lookup_and_mutation(
    db_session, member, other_member
):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'event', 'a.xlsx', [{'kind': '1'}])

    assert repo.get_owned(member.id, workspace.id).id == workspace.id

    for owner_id, workspace_id in (
        (other_member.id, workspace.id),
        (member.id, 'missing-workspace'),
    ):
        with pytest.raises(WorkspaceNotFound):
            repo.get_owned(owner_id, workspace_id)
        with pytest.raises(WorkspaceNotFound):
            repo.delete_owned(owner_id, workspace_id)
        with pytest.raises(WorkspaceNotFound):
            repo.replace_template(owner_id, workspace_id, 'b.xlsx', [])
        with pytest.raises(WorkspaceNotFound):
            repo.save_results(
                owner_id, workspace_id, game='cabal', results=[], not_found=[]
            )

    assert repo.get_owned(member.id, workspace.id).filename == 'a.xlsx'
    replaced = repo.replace_template(member.id, workspace.id, 'b.xlsx', [{'kind': '2'}])
    assert replaced.filename == 'b.xlsx'
    assert replaced.criteria == [{'kind': '2'}]
    saved = repo.save_results(
        member.id, workspace.id, game='cabal', results=[{'id': '10'}], not_found=['2']
    )
    assert (saved.game, saved.results, saved.not_found) == (
        'cabal', [{'id': '10'}], ['2']
    )

    repo.delete_owned(member.id, workspace.id)
    with pytest.raises(WorkspaceNotFound):
        repo.get_owned(member.id, workspace.id)


def test_pending_import_cannot_cross_users_or_attach_to_foreign_workspace(
    db_session, member, other_member
):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'shop')

    with pytest.raises(WorkspaceNotFound):
        repo.add_pending(other_member.id, workspace.id, [], [])
    with pytest.raises(WorkspaceNotFound):
        repo.add_pending(member.id, 'missing-workspace', [], [])

    pending = repo.add_pending(
        member.id, workspace.id, [('One', [{'kind': '1', 'sources': ['A']}])], ['skip']
    )
    for owner_id, pending_id in (
        (other_member.id, pending.id),
        (member.id, 'missing-pending'),
    ):
        with pytest.raises(PendingImportNotFound):
            repo.apply_pending(owner_id, pending_id, ['One'])

    applied = repo.apply_pending(member.id, pending.id, ['One'])
    assert applied.criteria == [{'kind': '1', 'sources': ['A']}]
    assert applied.occurrences == [{'kind': '1', 'sources': ['A']}]
    assert applied.skipped == ['skip']
    with pytest.raises(PendingImportNotFound):
        repo.apply_pending(member.id, pending.id, ['One'])


def test_apply_pending_merges_then_deletes_atomically(db_session, member, monkeypatch):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'event')
    pending = repo.add_pending(
        member.id, workspace.id, [('One', [{'kind': '1', 'sources': ['A']}])], []
    )

    def fail_merge(*_args, **_kwargs):
        raise RuntimeError('merge failed')

    monkeypatch.setattr('web.workspaces.merge_imported', fail_merge)
    with pytest.raises(RuntimeError, match='merge failed'):
        repo.apply_pending(member.id, pending.id, ['One'])

    unchanged = repo.get_owned(member.id, workspace.id)
    assert unchanged.criteria == []
    assert unchanged.occurrences == []

    from web.item_service import merge_imported

    monkeypatch.setattr('web.workspaces.merge_imported', merge_imported)
    applied = repo.apply_pending(member.id, pending.id, ['One'])
    assert applied.criteria == [{'kind': '1', 'sources': ['A']}]
    with pytest.raises(PendingImportNotFound):
        repo.apply_pending(member.id, pending.id, ['One'])


def test_two_pending_imports_preserve_both_merges(db_session, member):
    repo = WorkspaceRepository(db_session)
    workspace = repo.create(member.id, 'event')
    first = repo.add_pending(
        member.id, workspace.id, [('One', [{'kind': '1', 'sources': ['A']}])], []
    )
    second = repo.add_pending(
        member.id, workspace.id, [('Two', [{'kind': '2', 'sources': ['B']}])], []
    )

    repo.apply_pending(member.id, first.id, ['One'])
    applied = repo.apply_pending(member.id, second.id, ['Two'])

    assert [row['kind'] for row in applied.criteria] == ['1', '2']
    assert [row['kind'] for row in applied.occurrences] == ['1', '2']
