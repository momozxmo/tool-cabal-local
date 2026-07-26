from __future__ import annotations

import datetime as _dt

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from web.item_service import merge_imported, mode_policy, stamp_sheet_rows
from web.models import PendingImportRecord, WorkspaceRecord


def _json_safe(value):
    """Make a value safe for a JSON column.

    Spreadsheet cells can arrive as datetime/date/time objects (openpyxl reads
    dated cells that way), which the JSON encoder cannot serialize. Convert those
    to ISO strings, recursing through dicts/lists so nested row values are also
    covered.
    """
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    return value


class WorkspaceNotFound(LookupError):
    pass


class PendingImportNotFound(LookupError):
    pass


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self, owner_user_id: str, mode: str, filename: str = '',
        criteria: list[dict] | None = None,
    ) -> WorkspaceRecord:
        mode_policy(mode)
        workspace = WorkspaceRecord(
            owner_user_id=owner_user_id,
            mode=mode,
            filename=filename,
            criteria=[_json_safe(dict(row)) for row in (criteria or [])],
            occurrences=[],
        )
        self._session.add(workspace)
        self._session.flush()
        return workspace

    def get_owned(
        self, owner_user_id: str, workspace_id: str,
    ) -> WorkspaceRecord:
        workspace = self._session.scalar(
            select(WorkspaceRecord).where(
                WorkspaceRecord.id == workspace_id,
                WorkspaceRecord.owner_user_id == owner_user_id,
            )
        )
        if workspace is None:
            raise WorkspaceNotFound()
        return workspace

    def delete_owned(self, owner_user_id: str, workspace_id: str) -> None:
        result = self._session.execute(
            delete(WorkspaceRecord).where(
                WorkspaceRecord.id == workspace_id,
                WorkspaceRecord.owner_user_id == owner_user_id,
            )
        )
        if result.rowcount != 1:
            raise WorkspaceNotFound()

    def replace_template(
        self, owner_user_id: str, workspace_id: str, filename: str,
        criteria: list[dict],
    ) -> WorkspaceRecord:
        workspace = self._update_workspace(
            owner_user_id,
            workspace_id,
            filename=filename,
            criteria=[dict(row) for row in criteria],
            occurrences=[],
            group_meta={},
            skipped=[],
            results=[],
            not_found=[],
        )
        return workspace

    def add_pending(
        self, owner_user_id: str, workspace_id: str, sheets: list,
        skipped: list,
    ) -> PendingImportRecord:
        self.get_owned(owner_user_id, workspace_id)
        pending = PendingImportRecord(
            owner_user_id=owner_user_id,
            workspace_id=workspace_id,
            sheets=[
                (sheet_name, [_json_safe(dict(row)) for row in rows])
                for sheet_name, rows in sheets
            ],
            skipped=_json_safe(list(skipped)),
        )
        self._session.add(pending)
        self._session.flush()
        return pending

    def apply_pending(
        self, owner_user_id: str, pending_id: str, selected_sheets: list[str],
    ) -> WorkspaceRecord:
        with self._session.begin_nested():
            pending = self._session.scalar(
                select(PendingImportRecord).where(
                    PendingImportRecord.id == pending_id,
                    PendingImportRecord.owner_user_id == owner_user_id,
                ).with_for_update()
            )
            if pending is None:
                raise PendingImportNotFound()

            workspace = self._session.scalar(
                select(WorkspaceRecord).where(
                    WorkspaceRecord.id == pending.workspace_id,
                    WorkspaceRecord.owner_user_id == owner_user_id,
                ).with_for_update()
            )
            if workspace is None:
                raise PendingImportNotFound()

            selected = set(selected_sheets)
            items = []
            for sheet_name, rows in pending.sheets:
                if sheet_name in selected:
                    items.extend(
                        stamp_sheet_rows(sheet_name, rows)
                        if workspace.mode == 'event' else rows)
            merged = merge_imported(
                workspace.criteria, workspace.occurrences, workspace.group_meta, items
            )
            workspace = self._update_workspace(
                owner_user_id,
                workspace.id,
                criteria=merged.criteria,
                occurrences=merged.occurrences,
                group_meta=merged.group_meta,
                skipped=list(workspace.skipped) + list(pending.skipped),
                results=[],
                not_found=[],
            )
            deleted = self._session.execute(
                delete(PendingImportRecord).where(
                    PendingImportRecord.id == pending.id,
                    PendingImportRecord.owner_user_id == owner_user_id,
                )
            )
            if deleted.rowcount != 1:
                raise PendingImportNotFound()
            return workspace

    def save_results(
        self, owner_user_id: str, workspace_id: str, *, game: str, results: list,
        not_found: list,
    ) -> WorkspaceRecord:
        return self._update_workspace(
            owner_user_id,
            workspace_id,
            game=game,
            results=list(results),
            not_found=list(not_found),
        )

    def _update_workspace(
        self, owner_user_id: str, workspace_id: str, **values,
    ) -> WorkspaceRecord:
        # Every JSON column funnels through here; sanitize so spreadsheet-sourced
        # datetime cells never reach the JSON encoder.
        values = {key: _json_safe(item) for key, item in values.items()}
        workspace = self._session.scalar(
            update(WorkspaceRecord).where(
                WorkspaceRecord.id == workspace_id,
                WorkspaceRecord.owner_user_id == owner_user_id,
            ).values(**values).returning(WorkspaceRecord)
        )
        if workspace is None:
            raise WorkspaceNotFound()
        return workspace
