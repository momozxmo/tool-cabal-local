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


def test_result_view():
    item = {'aztek_id': '221070', 'item_name': 'Force Wing', 'sources': ['Cash Shop'],
            '_desc': 'แฟชั่น', 'web': 'yes', 'img': 'yes'}
    v = sr.result_view(item)
    check('result_view id/name', v['aztek_id'] == '221070' and v['item_name'] == 'Force Wing')
    check('result_view groups joins sources', v['groups'] == 'Cash Shop')
    check('result_view desc', v['desc'] == 'แฟชั่น')
    check('result_view params is string', isinstance(v['params'], str) and v['params'])


if __name__ == '__main__':
    test_binding_and_callbacks()
    test_engine_method_runs_on_fake_page()
    test_build_search_data()
    test_result_view()
    print('\n' + ('ALL PASS' if not FAIL else 'FAIL: ' + ', '.join(FAIL)))
    sys.exit(1 if FAIL else 0)
