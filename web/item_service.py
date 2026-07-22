# -*- coding: utf-8 -*-
"""GUI-free Item Finder helpers shared by the web endpoints.

This module contains only deterministic data transforms and byte exporters.
It deliberately does not know about FastAPI, tkinter, or browser sessions.
"""
from dataclasses import dataclass
from datetime import datetime
import csv
import io
import threading
import uuid

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

import event_tool
import item_finder


_WORKBOOK_PARSE_LOCK = threading.Lock()


def parse_workbook_locked(parser, path):
    """Serialize parsers that temporarily monkey-patch openpyxl internals."""
    with _WORKBOOK_PARSE_LOCK:
        return parser(path)


@dataclass
class MergeResult:
    criteria: list
    occurrences: list
    group_meta: dict
    added: int
    merged: int


@dataclass
class Workspace:
    id: str
    mode: str
    filename: str
    criteria: list
    occurrences: list
    group_meta: dict
    skipped: list
    results: list
    not_found: list
    game: str = ''


@dataclass
class PendingImport:
    id: str
    workspace_id: str
    sheets: list
    skipped: list


class WorkspaceStore:
    """Small in-memory store for the local MVP; API shape can later use Postgres."""
    def __init__(self):
        self._workspaces = {}
        self._pending = {}
        self._lock = threading.RLock()

    def create(self, mode, filename='', criteria=None):
        with self._lock:
            mode_policy(mode)
            workspace = Workspace(
                id=uuid.uuid4().hex, mode=mode, filename=filename,
                criteria=[dict(row) for row in (criteria or [])], occurrences=[],
                group_meta={}, skipped=[], results=[], not_found=[])
            self._workspaces[workspace.id] = workspace
            return workspace

    def get(self, workspace_id):
        with self._lock:
            return self._workspaces[workspace_id]

    def delete(self, workspace_id):
        with self._lock:
            del self._workspaces[workspace_id]

    def replace_template(self, workspace_id, filename, criteria):
        with self._lock:
            workspace = self.get(workspace_id)
            workspace.filename = filename
            workspace.criteria = [dict(row) for row in criteria]
            workspace.occurrences = []
            workspace.group_meta = {}
            workspace.skipped = []
            workspace.results = []
            workspace.not_found = []
            return workspace

    def add_pending(self, workspace_id, sheets, skipped=None):
        with self._lock:
            self.get(workspace_id)
            pending = PendingImport(uuid.uuid4().hex, workspace_id,
                                    [(name, [dict(row) for row in rows])
                                     for name, rows in sheets], list(skipped or []))
            self._pending[pending.id] = pending
            return pending

    def pending(self, pending_id):
        with self._lock:
            return self._pending[pending_id]

    def apply_pending(self, pending_id, selected_sheets):
        with self._lock:
            pending = self._pending.pop(pending_id)
            workspace = self.get(pending.workspace_id)
            selected = set(selected_sheets)
            items = []
            for sheet_name, rows in pending.sheets:
                if sheet_name in selected:
                    items.extend(rows)
            merged = merge_imported(workspace.criteria, workspace.occurrences,
                                    workspace.group_meta, items)
            workspace.criteria = merged.criteria
            workspace.occurrences = merged.occurrences
            workspace.group_meta = merged.group_meta
            workspace.skipped.extend(pending.skipped)
            workspace.results = []
            workspace.not_found = []
            return workspace


def parser_for_mode(mode):
    parsers = {
        'event': event_tool.parse_event_plan_workbook,
        'itemcode': item_finder.parse_event_workbook,
        'shop': item_finder.parse_shop_workbook,
    }
    try:
        return parsers[mode]
    except KeyError:
        raise ValueError('ไม่รู้จักโหมด: %s' % mode)


def mode_policy(mode):
    policies = {
        'event': {'web_mode': 'any', 'web_locked': False, 'read_desc': False},
        'itemcode': {'web_mode': 'no', 'web_locked': True, 'read_desc': False},
        'shop': {'web_mode': 'no', 'web_locked': False, 'read_desc': True},
    }
    if mode not in policies:
        raise ValueError('ไม่รู้จักโหมด: %s' % mode)
    return dict(policies[mode])


def _criteria_key(row):
    return (str(row.get('kind', '') or ''), str(row.get('opt', '') or ''),
            str(row.get('dur', '') or ''), str(row.get('name', '') or '').strip())


def merge_imported(criteria, occurrences, group_meta, items):
    """Mirror App._apply_event_items without any widget dependencies."""
    criteria = [dict(row) for row in criteria]
    occurrences = [dict(row) for row in occurrences]
    group_meta = dict(group_meta)
    index = {}
    for row in criteria:
        row.setdefault('sources', [])
        index[_criteria_key(row)] = row

    added = merged = 0
    for source in items:
        row = dict(source)
        row['sources'] = list(row.get('sources') or [])
        meta = row.pop('group_meta', None)
        if meta:
            for group in row['sources']:
                group_meta[group] = dict(meta)
        occurrences.append(dict(row))
        key = _criteria_key(row)
        if key in index:
            target = index[key]
            for group in row['sources']:
                if group not in target['sources']:
                    target['sources'].append(group)
                    merged += 1
        else:
            criteria.append(row)
            index[key] = row
            added += 1
    return MergeResult(criteria, occurrences, group_meta, added, merged)


def regroup_results(results, occurrences):
    """Expand found rows back into document/group order, matching desktop."""
    if not occurrences or not results:
        return [dict(row) for row in results]
    found = {}
    for row in results:
        key = (str(row.get('item_kind', '') or '').strip(),
               str(row.get('item_option', '') or '').strip(),
               str(row.get('duration_index', '') or '').strip())
        bucket = found.setdefault(key, [])
        if not any(old.get('aztek_id') == row.get('aztek_id') for old in bucket):
            bucket.append(row)
    expanded = []
    for occurrence in occurrences:
        key = (str(occurrence.get('kind', '') or '').strip(),
               str(occurrence.get('opt', '') or '').strip(),
               str(occurrence.get('dur', '') or '').strip())
        for found_row in found.get(key, []):
            row = dict(found_row)
            row['sources'] = list(occurrence.get('sources') or [])
            row['file_name'] = occurrence.get('name', '') or ''
            expanded.append(row)
    return expanded or [dict(row) for row in results]


def _bundle_name(group, group_meta):
    meta = group_meta.get(group) or {}
    sheet = str(meta.get('shop_sheet') or meta.get('activity') or '').strip()
    return '%s - %s' % (sheet, group) if sheet and not group.startswith(sheet) else group


def build_bundles(results, group_meta):
    """Build one ordered bundle per group; shared item IDs are always last."""
    item_groups = {}
    for row in results:
        item_id = str(row.get('aztek_id', '') or '').strip()
        if not item_id:
            continue
        groups = row.get('sources') or ['(ไม่มีกลุ่ม)']
        item_groups.setdefault(item_id, set()).update(
            str(g or '').strip() or '(ไม่มีกลุ่ม)' for g in groups)

    order, grouped = [], {}
    for row in results:
        item_id = str(row.get('aztek_id', '') or '').strip()
        if not item_id:
            continue
        shared = len(item_groups.get(item_id, ())) > 1
        for raw_group in (row.get('sources') or ['(ไม่มีกลุ่ม)']):
            group = str(raw_group or '').strip() or '(ไม่มีกลุ่ม)'
            if group not in grouped:
                grouped[group] = {'seen': set(), 'normal': [], 'shared': []}
                order.append(group)
            bucket = grouped[group]
            if item_id in bucket['seen']:
                continue
            bucket['seen'].add(item_id)
            item = {'id': item_id, 'name': row.get('item_name', '') or ''}
            bucket['shared' if shared else 'normal'].append(item)
    return [
        {'name': _bundle_name(group, group_meta), 'group': group,
         'items': grouped[group]['normal'] + grouped[group]['shared']}
        for group in order
    ]


_EXPORT_HEADERS = ['#', 'aztek_id', 'item_name', 'item_kind', 'item_option',
                   'duration_index', 'game', 'notes', 'criteria_no', 'groups',
                   'description']


def _safe_cell(value):
    """Prevent CSV/XLSX formula execution while preserving displayed text."""
    if isinstance(value, str) and value.startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _export_row(index, item):
    values = [index, item.get('aztek_id', ''), item.get('item_name', ''),
              item.get('item_kind', ''), item.get('item_option', ''),
              item.get('duration_index', ''), item.get('game', ''),
              item.get('notes', 'passed'), item.get('_ci', ''),
              ' | '.join(item.get('sources') or []), item.get('_desc', '')]
    return [_safe_cell(value) for value in values]


def export_csv_bytes(results):
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(_EXPORT_HEADERS)
    for index, item in enumerate(results, 1):
        writer.writerow(_export_row(index, item))
    return ('\ufeff' + out.getvalue()).encode('utf-8')


def export_xlsx_bytes(results, game):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Results'
    header_fill = PatternFill('solid', fgColor='1F6FEB')
    row_fill = PatternFill('solid', fgColor='1A3A1A')
    white = Font(color='FFFFFF', bold=True)
    green = Font(color='3FB950')
    gray_fill = PatternFill('solid', fgColor='21262D')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summaries = [
        'Aztek Item Finder — Export  |  เกม: %s  |  วันที่: %s' % (game, timestamp),
        'พบทั้งหมด %d items  |  สร้างโดย All for Cabal Web' % len(results), '',
    ]
    for row_index, text in enumerate(summaries, 1):
        cell = sheet.cell(row=row_index, column=1, value=text)
        cell.font = Font(italic=True, color='8B949E', size=9)
        cell.fill = gray_fill
        sheet.merge_cells(start_row=row_index, start_column=1, end_row=row_index, end_column=11)

    xlsx_headers = ['#', 'Aztek ID', 'Item Name', 'ItemKind', 'itemOption',
                    'durationIndex', 'Game', 'Notes', 'Criteria #',
                    'Groups (อยู่ตารางไหนบ้าง)', 'คำอธิบายไอเทม']
    widths = [5, 12, 30, 12, 14, 16, 14, 24, 10, 42, 40]
    for column, (header, width) in enumerate(zip(xlsx_headers, widths), 1):
        cell = sheet.cell(row=4, column=column, value=header)
        cell.fill = header_fill
        cell.font = white
        cell.alignment = Alignment(horizontal='center')
        sheet.column_dimensions[cell.column_letter].width = width
    for index, item in enumerate(results, 1):
        sheet.append(_export_row(index, item))
        row_index = 4 + index
        for column in range(1, 12):
            cell = sheet.cell(row=row_index, column=column)
            cell.fill = row_fill
            cell.font = green
            cell.alignment = Alignment(
                horizontal='center' if column in (1, 2, 4, 5, 6, 7, 9) else 'left')
    sheet.auto_filter.ref = 'A4:K4'
    sheet.freeze_panes = 'A5'
    out = io.BytesIO()
    workbook.save(out)
    return out.getvalue()
