# -*- coding: utf-8 -*-
"""รัน Item Finder แบบ headless สำหรับเว็บ โดย reuse เมธอด engine เดิมจาก item_finder.App
ตรง ๆ (bind เมธอดเข้ากับคลาสเบา ๆ ที่ป้อน callback แทน widget) — ไม่ก็อปโค้ด ไม่สร้าง Tk root

ข้อจำกัด MVP: ใช้ CHROME_PROFILE เดิม (ต้องเคย login aztek ผ่านแอป desktop มาก่อน) และห้ามเปิด
แอป desktop พร้อมกัน (โปรไฟล์ถูกล็อกไม่ให้เปิดซ้ำ)
"""
import item_finder


class _StubWidget:
    """แทน tk widget (nb/root) — รับ .select()/.after() แบบไม่ทำอะไร"""
    def select(self, *a, **k):
        pass

    def after(self, *a, **k):
        pass


class HeadlessFinder:
    """โฮสต์ของ engine ค้นหา: ป้อน state + callback แล้วให้เมธอดเดิมของ App ทำงานบนนี้"""

    def __init__(self, on_log, on_result, on_progress):
        self._on_log = on_log
        self._on_result = on_result
        self._on_progress = on_progress
        self._cancel = False
        self._results = []
        self._occurrences = []          # ว่าง = ข้าม _regroup_results (ผลเรียงตามที่ค้นเจอ)
        self._not_found = []
        self._pager_dumped = False
        self.nb = _StubWidget()
        self.root = _StubWidget()

    # --- callback แทน GUI (เมธอด engine เรียกพวกนี้) ---
    def log(self, msg, level='INFO'):
        self._on_log(str(msg), level)

    def add_result_row(self, item):
        self._on_result(item)

    def set_progress(self, cur, total, name):
        self._on_progress(cur, total, name)

    def _update_count(self):
        pass

    def _regroup_results(self):
        pass


# reuse เมธอด engine เดิมทั้งดุ้น (function object เดิม -> __globals__ ยังชี้ item_finder
# ทำให้ helper/ค่าคงที่ภายใน เช่น web_values_summary/_norm_name/SEL/CHROME_PROFILE resolve เองหมด)
_ENGINE_METHODS = (
    '_auto', '_search_all', '_wait_table_ready', '_wait_detail_ready',
    '_apply_filters', '_read_all_pages', '_dump_pager', '_read_table_page',
    '_go_next_page', '_run_deep_check', '_check_item_detail', '_go_back',
)
for _name in _ENGINE_METHODS:
    setattr(HeadlessFinder, _name, getattr(item_finder.App, _name))
del _name


def build_search_data(game, criteria, web_mode='any'):
    """สร้าง data dict แบบเดียวกับ App._start (โหมด multi) จาก template + ตัวเลือกแสดงผลบนเว็บ"""
    if game not in item_finder.GAMES:
        raise ValueError('ไม่รู้จักเกม: %s' % game)
    multi = [dict(r) for r in criteria]

    if web_mode in ('yes', 'no'):
        def _needs_web(r):
            return (r.get('trade', 'any') != 'any' or r.get('drill', 'any') != 'any'
                    or str(r.get('qty_val', '') or '').strip()
                    or str(r.get('crit_val', '') or '').strip())
        for r in multi:
            if web_mode == 'no' and _needs_web(r):
                r['web'] = 'yes'
            else:
                r['web'] = web_mode
        if web_mode == 'yes':
            for r in multi:
                r['_show_web_vals'] = True

    def _row_has_deep(r):
        return (r.get('web', 'any') != 'any' or r.get('img', 'any') != 'any'
                or r.get('qty_val', '') != '' or r.get('trade', 'any') != 'any'
                or r.get('drill', 'any') != 'any' or r.get('crit_val', '') != '')

    auto_deep = any(_row_has_deep(r) for r in multi)
    return {
        'game': game, 'url': item_finder.GAMES[game], 'multi': multi,
        'deep': auto_deep, 'web': 'any', 'img': 'any', 'qty_val': '',
        'trade': 'any', 'drill': 'any', 'crit_val': '', 'batch': 10,
        'headless': True, 'read_desc': False,
    }


def result_view(item):
    """แปลง item ที่ผ่าน -> dict สำหรับโชว์บนเว็บ (คอลัมน์เหมือนตารางผลใน desktop)"""
    params = item_finder.deep_summary(item)
    wv = item.get('_web_vals')
    if wv:
        params = (params + ' | ' + wv) if params and params != '-' else wv
    return {
        'aztek_id': item.get('aztek_id', ''),
        'item_name': item.get('item_name', ''),
        'file_name': item.get('file_name', '') or '',
        'params': params,
        'groups': ' , '.join(item.get('sources', []) or []),
        'desc': item.get('_desc', '') or '',
    }
