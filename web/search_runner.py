# -*- coding: utf-8 -*-
"""Callback-driven host for the existing Item Finder Playwright engine."""
from playwright.async_api import async_playwright

import item_finder
from web import item_service


class AztekSessionExpired(Exception):
    """The stored Aztek session no longer authenticates against the site."""


async def is_login_page(page):
    """Heuristic: is this the Aztek login screen rather than the app shell?

    Uses the URL path and the presence of a password field — never an empty
    result table, which is a legitimate search outcome, not an expired session.
    """
    url = (getattr(page, 'url', '') or '').lower()
    if any(part in url for part in ('/login', '/signin', '/sign-in', '/auth')):
        return True
    try:
        has_password = await page.evaluate(
            "() => !!document.querySelector("
            "'input[type=\"password\"], input[name=\"password\"]')")
    except Exception:
        has_password = False
    return bool(has_password)


class _StubNotebook:
    def select(self, *args, **kwargs):
        return None


class _ImmediateRoot:
    """Execute Tk-style after callbacks immediately on the asyncio thread."""
    def after(self, delay, callback=None, *args):
        if callback:
            return callback(*args)
        return None


class HeadlessFinder:
    def __init__(self, on_log, on_result, on_progress, *, occurrences=None,
                 on_reset=None):
        self._on_log = on_log
        self._on_result = on_result
        self._on_progress = on_progress
        self._on_reset = on_reset or (lambda: None)
        self._cancel = False
        self._results = []
        self._occurrences = [dict(row) for row in (occurrences or [])]
        self._not_found = []
        self._pager_dumped = False
        self.nb = _StubNotebook()
        self.root = _ImmediateRoot()

    def log(self, message, level='INFO'):
        self._on_log(str(message), level)

    def add_result_row(self, item):
        self._on_result(item)

    def set_progress(self, current, total, name):
        self._on_progress(current, total, name)

    def _update_count(self):
        return None

    def _regroup_results(self):
        if not self._occurrences or not self._results:
            return None
        rows = item_service.regroup_results(self._results, self._occurrences)
        if rows == self._results:
            return None
        self._results = rows
        self._on_reset()
        for row in rows:
            self._on_result(row)
        self.log('เรียงผลลัพธ์ตามชุด (เอกสาร) — %d แถว' % len(rows), 'SUCCESS')
        return None

    async def run(self, data, storage_state):
        """Run one search in a fresh, non-persistent context for this user.

        Unlike the desktop ``_auto`` (which reuses a shared persistent Chrome
        profile), the web path launches a throwaway browser seeded only with the
        caller's decrypted Aztek storage state, so users never share a session.
        """
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=storage_state)
            page = await context.new_page()
            try:
                await page.goto(data['url'], wait_until='domcontentloaded',
                                timeout=30000)
                await page.wait_for_timeout(2000)  # let the SPA settle
                if await is_login_page(page):
                    raise AztekSessionExpired('Aztek session หมดอายุ')
                await self._search_all(page, data)
            finally:
                await context.close()
                await browser.close()


_ENGINE_METHODS = (
    '_auto', '_search_all', '_wait_table_ready', '_wait_detail_ready',
    '_apply_filters', '_read_all_pages', '_dump_pager', '_read_table_page',
    '_go_next_page', '_run_deep_check', '_check_item_detail', '_go_back',
)
for _method_name in _ENGINE_METHODS:
    setattr(HeadlessFinder, _method_name, getattr(item_finder.App, _method_name))
del _method_name


def build_search_data(game, criteria, web_mode=None, *, mode='event'):
    """Build the same multi-search data as desktop, including mode policy."""
    if game not in item_finder.GAMES:
        raise ValueError('ไม่รู้จักเกม: %s' % game)
    policy = item_service.mode_policy(mode)
    if policy['web_locked']:
        web_mode = policy['web_mode']
    elif web_mode is None:
        web_mode = policy['web_mode']
    if web_mode not in ('any', 'yes', 'no'):
        raise ValueError('ค่าแสดงผลบนเว็บไม่ถูกต้อง: %s' % web_mode)

    multi = [dict(row) for row in criteria]
    if web_mode in ('yes', 'no'):
        def needs_web(row):
            return (row.get('trade', 'any') != 'any'
                    or row.get('drill', 'any') != 'any'
                    or str(row.get('qty_val', '') or '').strip()
                    or str(row.get('crit_val', '') or '').strip())

        for row in multi:
            row['web'] = 'yes' if web_mode == 'no' and needs_web(row) else web_mode
            if web_mode == 'yes':
                row['_show_web_vals'] = True

    def has_deep(row):
        return (row.get('web', 'any') != 'any'
                or row.get('img', 'any') != 'any'
                or row.get('qty_val', '') != ''
                or row.get('trade', 'any') != 'any'
                or row.get('drill', 'any') != 'any'
                or row.get('crit_val', '') != '')

    return {
        'game': game,
        'url': item_finder.GAMES[game],
        'multi': multi,
        # Shop must visit every detail page to read textarea[name="detail"],
        # even when every filter in a generic template is Any.
        'deep': policy['read_desc'] or any(has_deep(row) for row in multi),
        'web': 'any', 'img': 'any', 'qty_val': '', 'trade': 'any',
        'drill': 'any', 'crit_val': '', 'batch': 10,
        'headless': True,
        'read_desc': policy['read_desc'],
    }


def result_view(item):
    params = item_finder.deep_summary(item)
    web_values = item.get('_web_vals')
    if web_values:
        params = ((params + ' | ' + web_values)
                  if params and params != '-' else web_values)
    return {
        'aztek_id': item.get('aztek_id', ''),
        'item_name': item.get('item_name', ''),
        'file_name': item.get('file_name', '') or '',
        'item_kind': item.get('item_kind', '') or '',
        'item_option': item.get('item_option', '') or '',
        'duration_index': item.get('duration_index', '') or '',
        'game': item.get('game', '') or '',
        'notes': item.get('notes', '') or '',
        'criteria_no': item.get('_ci', '') or '',
        'params': params,
        'groups': ' , '.join(item.get('sources') or []),
        'desc': item.get('_desc', '') or '',
    }
