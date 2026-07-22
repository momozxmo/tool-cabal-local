# -*- coding: utf-8 -*-
"""ยืนยัน web/search_runner: HeadlessFinder bind engine เดิมได้ + build_search_data + result_view
(ทดสอบได้โดยไม่ต้องต่อ aztek จริง — ใช้ fake page)"""
import os
import sys
import asyncio

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from web import search_runner as sr  # noqa: E402
import item_finder  # noqa: E402

FAIL = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else '*** FAIL *** ') + name + (('  ' + extra) if extra else ''))
    if not cond:
        FAIL.append(name)
    assert cond, name + ((' — ' + extra) if extra else '')


class FakePage:
    async def evaluate(self, js, *a):
        return []

    async def wait_for_timeout(self, ms):
        pass


def test_binding_and_callbacks():
    logs, results, progs = [], [], []
    hf = sr.HeadlessFinder(
        lambda m, level='INFO': logs.append((m, level)),
        lambda it: results.append(it),
        lambda c, t, n: progs.append((c, t, n)))
    for m in ('_auto', '_search_all', '_check_item_detail', '_read_all_pages',
              '_read_table_page', '_go_next_page', '_go_back', '_wait_table_ready',
              '_wait_detail_ready', '_apply_filters', '_dump_pager', '_run_deep_check'):
        check('bound engine method %s' % m, callable(getattr(hf, m, None)))
    hf.log('hello', 'STEP'); hf.add_result_row({'x': 1}); hf.set_progress(1, 5, 'z')
    check('log -> callback', logs == [('hello', 'STEP')])
    check('add_result_row -> callback', results == [{'x': 1}])
    check('set_progress -> callback', progs == [(1, 5, 'z')])
    check('_update_count/_regroup_results no-op', hf._update_count() is None and hf._regroup_results() is None)


def test_regroup_callback_replaces_streamed_rows_in_document_order():
    results, resets = [], []
    occurrences = [
        {'kind': '1', 'opt': '', 'dur': '', 'name': 'A', 'sources': ['G1']},
        {'kind': '2', 'opt': '', 'dur': '', 'name': 'B', 'sources': ['G1']},
        {'kind': '1', 'opt': '', 'dur': '', 'name': 'A', 'sources': ['G2']},
    ]
    hf = sr.HeadlessFinder(
        lambda *a, **k: None, lambda row: results.append(row), lambda *a: None,
        occurrences=occurrences, on_reset=lambda: resets.append(True))
    hf._results = [
        {'aztek_id': '10', 'item_kind': '1', 'item_option': '',
         'duration_index': '', 'item_name': 'A web'},
        {'aztek_id': '20', 'item_kind': '2', 'item_option': '',
         'duration_index': '', 'item_name': 'B web'},
    ]
    hf._regroup_results()
    check('regroup resets streamed table once', resets == [True])
    check('regroup follows occurrence order',
          [r['aztek_id'] for r in hf._results] == ['10', '20', '10'])
    check('regroup re-emits final rows', results == hf._results)


def test_engine_method_runs_on_fake_page():
    hf = sr.HeadlessFinder(lambda *a, **k: None, lambda *a: None, lambda *a: None)
    fp = FakePage()
    rows = asyncio.run(hf._read_table_page(fp))
    check('_read_table_page returns evaluate() result', rows == [])
    hf._cancel = True
    r = asyncio.run(hf._wait_table_ready(fp))
    check('_wait_table_ready respects _cancel (returns falsy fast)', not r)


def test_build_search_data():
    game = item_finder.GAME_NAMES[0]
    crit = [{'kind': '1', 'opt': '', 'dur': '', 'name': 'x',
             'web': 'yes', 'img': 'any', 'qty_val': '', 'trade': 'any',
             'drill': 'any', 'crit_val': ''}]
    d = sr.build_search_data(game, crit, 'no')
    check('data game/url set', d['game'] == game and d['url'] == item_finder.GAMES[game])
    check('web_mode=no overrides row web', d['multi'][0]['web'] == 'no', str(d['multi'][0].get('web')))
    check('deep auto True (row has web)', d['deep'] is True)
    check('headless True', d['headless'] is True)

    d2 = sr.build_search_data(game, crit, 'yes')
    check('web_mode=yes -> web yes + _show_web_vals', d2['multi'][0]['web'] == 'yes'
          and d2['multi'][0].get('_show_web_vals') is True)

    try:
        sr.build_search_data('NOPE_GAME', crit, 'any')
        check('unknown game raises', False)
    except ValueError:
        check('unknown game raises', True)

    blank = [{'kind': '1', 'opt': '', 'dur': '', 'name': 'x',
              'web': 'any', 'img': 'any', 'qty_val': '', 'trade': 'any',
              'drill': 'any', 'crit_val': ''}]
    shop = sr.build_search_data(game, blank, 'any', mode='shop')
    check('shop defaults web=no and reads description',
          shop['read_desc'] is True and shop['deep'] is True)
    itemcode = sr.build_search_data(game, crit, 'yes', mode='itemcode')
    check('itemcode locks web=no even if caller asks yes',
          itemcode['multi'][0]['web'] == 'no' and itemcode['read_desc'] is False)


def test_result_view():
    item = {'aztek_id': '221070', 'item_name': 'Force Wing', 'sources': ['Cash Shop'],
            '_desc': 'แฟชั่น', 'web': 'yes', 'img': 'yes'}
    v = sr.result_view(item)
    check('result_view id/name', v['aztek_id'] == '221070' and v['item_name'] == 'Force Wing')
    check('result_view groups joins sources', v['groups'] == 'Cash Shop')
    check('result_view desc', v['desc'] == 'แฟชั่น')
    check('result_view params is string', isinstance(v['params'], str) and v['params'])


class _FakeRunPage:
    def __init__(self, url='https://aztek-tools.combo-interactive.com/items'):
        self.url = url

    async def goto(self, *a, **k):
        return None

    async def wait_for_timeout(self, ms):
        return None

    async def evaluate(self, js, *a):
        return False  # no password field -> not the login page


class _FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    async def new_page(self):
        return self.page

    async def close(self):
        self.closed = True


class _FakeBrowser:
    def __init__(self, page):
        self.context = _FakeContext(page)
        self.new_context_calls = []
        self.closed = False

    async def new_context(self, **kw):
        self.new_context_calls.append(kw)
        return self.context

    async def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, page):
        self.browser = _FakeBrowser(page)
        self.launch_calls = []
        self.persistent_calls = []

    async def launch(self, **kw):
        self.launch_calls.append(kw)
        return self.browser

    async def launch_persistent_context(self, **kw):
        self.persistent_calls.append(kw)
        return self.browser


class _FakePlaywright:
    def __init__(self, page=None):
        self.chromium = _FakeChromium(page or _FakeRunPage())

    @property
    def browser(self):
        return self.chromium.browser

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _run_data():
    game = item_finder.GAME_NAMES[0]
    return {'game': game, 'url': item_finder.GAMES[game], 'multi': [],
            'deep': False, 'headless': True, 'read_desc': False}


def test_web_runner_uses_non_persistent_context(monkeypatch):
    storage_state = {'cookies': [{'name': 'a', 'value': 'b'}], 'origins': []}
    fake = _FakePlaywright()
    monkeypatch.setattr(sr, 'async_playwright', lambda: fake)
    finder = sr.HeadlessFinder(lambda *a, **k: None, lambda *a: None, lambda *a: None)

    asyncio.run(finder.run(_run_data(), storage_state))

    check('web runner launches non-persistent headless chromium',
          fake.chromium.launch_calls == [{'headless': True}])
    check('web runner seeds a context with storage_state only',
          fake.browser.new_context_calls == [{'storage_state': storage_state}])
    check('web runner never launches a persistent profile',
          fake.chromium.persistent_calls == [])
    check('web runner closes context and browser',
          fake.browser.closed and fake.browser.context.closed)


def test_web_runner_raises_on_login_page(monkeypatch):
    page = _FakeRunPage(url='https://aztek-tools.combo-interactive.com/login')
    fake = _FakePlaywright(page)
    monkeypatch.setattr(sr, 'async_playwright', lambda: fake)
    finder = sr.HeadlessFinder(lambda *a, **k: None, lambda *a: None, lambda *a: None)

    raised = False
    try:
        asyncio.run(finder.run(_run_data(), {'cookies': [], 'origins': []}))
    except sr.AztekSessionExpired:
        raised = True

    check('login page raises AztekSessionExpired', raised)
    check('runner still closes browser after expiry',
          fake.browser.closed and fake.browser.context.closed)


if __name__ == '__main__':
    test_binding_and_callbacks()
    test_regroup_callback_replaces_streamed_rows_in_document_order()
    test_engine_method_runs_on_fake_page()
    test_build_search_data()
    test_result_view()
    print('\n' + ('ALL PASS' if not FAIL else 'FAIL: ' + ', '.join(FAIL)))
    sys.exit(1 if FAIL else 0)
