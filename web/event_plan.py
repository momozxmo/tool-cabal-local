"""Turn the desktop Event parser's output into editable web Event drafts."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

import config as cfg


def _text(value) -> str:
    return str(value or '').strip()


def _stamp(value: datetime | None) -> str:
    return value.strftime('%Y-%m-%dT%H:%M:%S') if value else ''


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]


def make_sheet_key(sheet_name: str) -> str:
    """Stable internal identity for one worksheet."""
    return 'sheet-' + _digest(_text(sheet_name).casefold())


def make_group_key(sheet_name: str, group_name: str, ordinal: int = 1) -> str:
    """Stable reward-table identity; visible names may repeat across sheets."""
    source = '%s\0%d\0%s' % (
        make_sheet_key(sheet_name), int(ordinal), _text(group_name).casefold())
    return 'group-' + _digest(source)


def _slug(name: str, game: str, warnings: list[str]) -> str:
    made = re.sub(
        r'-+', '-',
        re.sub(r'[^a-z0-9-]', '',
               re.sub(r'\s+', '-', _text(name).lower())),
    ).strip('-')
    if not made:
        warnings.append(
            'ชื่อ Event สร้าง slug อัตโนมัติไม่ได้ กรุณากรอก slug เอง')
        return ''
    server = cfg.server_code(game)
    if server and not made.endswith('-' + server):
        made += '-' + server
    return made


def _end_value(raw, game: str, now: datetime,
               warnings: list[str]) -> datetime | None:
    from itemcode_tool import parse_expire

    end = parse_expire(raw, now)
    if end is None:
        warnings.append(
            'ไม่พบหรืออ่านวันสิ้นสุดจากเอกสารไม่ได้ กรุณากรอกก่อนดูตัวอย่าง')
        return None
    end = cfg.region_end_of_day(game, end)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if end <= start:
        warnings.append(
            'วันสิ้นสุดในเอกสารคือ %s ซึ่งผ่านมาแล้ว กรุณาตรวจสอบก่อนสร้าง'
            % end.strftime('%Y-%m-%d'))
    return end


def _reward(group: str, key: str) -> dict:
    name = _text(group)
    return {
        'group_key': key,
        'group': name,
        'name_th': name,
        'name_en': name,
        'uses_per_user': '1',
        'limited': False,
        'quantity': '',
        'remaining': '',
        'bundle_id': '',
    }


def build_event_draft(sheet_name: str, event: dict, game: str,
                      now: datetime | None = None) -> dict:
    """Build one Event draft from one parsed worksheet."""
    now = now or datetime.now()
    warnings: list[str] = []
    name = _text(event.get('name'))
    if not name:
        warnings.append(
            'ไม่พบชื่อ Event จากเอกสาร กรุณากรอกชื่อไทยและอังกฤษเอง')
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = _end_value(event.get('end_date') or event.get('end_event'),
                     game, now, warnings)
    rewards = []
    for ordinal, raw in enumerate(event.get('rewards') or [], 1):
        group = _text((raw or {}).get('name'))
        if not group:
            warnings.append(
                'ชุดรางวัลที่ %d ไม่มีชื่อ กรุณากรอกเอง' % ordinal)
        rewards.append(_reward(
            group, make_group_key(sheet_name, group, ordinal)))
    if len(rewards) == 1 and name:
        rewards[0]['name_th'] = name
        rewards[0]['name_en'] = name
    return {
        'sheet_key': make_sheet_key(sheet_name),
        'sheet': _text(sheet_name),
        'name_th': name,
        'name_en': name,
        'slug': _slug(name, game, warnings),
        'kind': 'WINNER',
        'uses_per_user': '1',
        'quantity': '0',
        'remaining': '0',
        'start_event': _stamp(start),
        'end_event': _stamp(end),
        'start_claim': _stamp(start),
        'end_claim': _stamp(end),
        'same_window': True,
        'group': '',
        'rewards': rewards,
        'warnings': warnings,
    }


def build_event_drafts(parsed_sheets: list, game: str,
                       now: datetime | None = None) -> list[dict]:
    return [
        build_event_draft(sheet_name, event, game, now=now)
        for sheet_name, event in parsed_sheets
        if (event or {}).get('rewards')
    ]


def build_workspace_events(group_meta: dict, game: str,
                           now: datetime | None = None,
                           group_keys: list[str] | None = None) -> list[dict]:
    """Reassemble selected Item Finder reward metadata into worksheet Events."""
    wanted = set(group_keys) if group_keys is not None else None
    sheets: dict[str, dict] = {}
    for internal_key, raw_meta in (group_meta or {}).items():
        if wanted is not None and internal_key not in wanted:
            continue
        meta = dict(raw_meta or {})
        key = _text(meta.get('group_key')) or _text(internal_key)
        sheet = _text(meta.get('sheet'))
        sheet_id = _text(meta.get('sheet_key')) or make_sheet_key(sheet)
        event = sheets.setdefault(sheet_id, {
            'sheet': sheet,
            'name': _text(meta.get('event_name') or meta.get('activity')),
            'end_date': meta.get('end_date') or meta.get('end_event'),
            'rewards': [],
        })
        if not event['name']:
            event['name'] = _text(meta.get('event_name') or meta.get('activity'))
        if not event['end_date']:
            event['end_date'] = meta.get('end_date') or meta.get('end_event')
        event['rewards'].append({
            'name': _text(meta.get('reward') or meta.get('group')),
            'group_key': key,
        })

    drafts = []
    for event in sheets.values():
        draft = build_event_draft(event['sheet'], event, game, now=now)
        for reward, source in zip(draft['rewards'], event['rewards']):
            reward['group_key'] = source['group_key']
        drafts.append(draft)
    return drafts
