# -*- coding: utf-8 -*-
"""
เทสต์ฟังก์ชัน pure (ไม่ต้องเปิด GUI/เว็บ) — รันเร็ว ป้องกันกฎที่แก้บ่อยพัง

รัน:  python -m pytest tests/ -q       (ถ้ามี pytest)
หรือ: python tests/test_pure.py        (รันตรง ๆ ไม่ต้องมี pytest)
"""
import os
import sys
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as cfg
from itemcode_tool import parse_expire, slugify


NOW = dt.datetime(2026, 7, 16, 10, 0, 0)


# --------------------------------------------------------------- parse_expire
def test_parse_expire_iso_with_T():
    assert parse_expire("2026-07-22T11:59:59", NOW) == dt.datetime(2026, 7, 22, 11, 59, 59)


def test_parse_expire_excel_serial():
    assert parse_expire("46265", NOW).date() == dt.date(2026, 8, 31)


def test_parse_expire_buddhist_era():
    # 2569 พ.ศ. -> 2026 ค.ศ.
    assert parse_expire("31/08/2569", NOW).date() == dt.date(2026, 8, 31)


def test_parse_expire_no_year_rolls_forward():
    # '01 Jan' ผ่านมาแล้วในปีนี้ -> ปีหน้า
    assert parse_expire("01 Jan", NOW).date() == dt.date(2027, 1, 1)


def test_parse_expire_no_year_future_same_year():
    assert parse_expire("31 Dec", NOW).date() == dt.date(2026, 12, 31)


def test_parse_expire_garbage_is_none():
    assert parse_expire("อะไรสักอย่าง", NOW) is None
    assert parse_expire("", NOW) is None
    assert parse_expire(None, NOW) is None


def test_parse_expire_random_count_not_a_date():
    # เลขจำนวนโค้ด (เช่น 1200) ต้องไม่ถูกอ่านเป็นวัน (นอกช่วง serial 40000-60000)
    assert parse_expire("1200", NOW) is None


# --------------------------------------------------------------- config: server_code
def test_server_code():
    assert cfg.server_code("CabalPC TH") == "pcth"
    assert cfg.server_code("CabalM SEA") == "msea"
    assert cfg.server_code("CabalPC SEA") == "pcsea"


# --------------------------------------------------------------- config: buffer
def test_code_buffer_pcth_is_10():
    assert cfg.code_buffer("CabalPC TH") == 10


def test_code_buffer_others_is_5():
    for g in ("CabalM TH", "CabalM SEA", "CabalPC SEA"):
        assert cfg.code_buffer(g) == 5


# --------------------------------------------------------------- config: region end time
def test_region_end_of_day_th():
    d = dt.datetime(2026, 7, 22, 11, 0, 0)
    assert cfg.region_end_of_day("CabalPC TH", d).strftime("%H:%M:%S") == "23:59:59"


def test_region_end_of_day_sea():
    d = dt.datetime(2026, 7, 22, 11, 0, 0)
    assert cfg.region_end_of_day("CabalPC SEA", d).strftime("%H:%M:%S") == "22:59:59"


def test_region_end_of_day_keeps_date():
    d = dt.datetime(2026, 7, 22, 11, 0, 0)
    out = cfg.region_end_of_day("CabalM TH", d)
    assert out.date() == dt.date(2026, 7, 22)


# --------------------------------------------------------------- config: keyword tables
def test_kw_hit_repeat_thai_and_eng():
    assert cfg.kw_hit("Can be repeated", cfg.KW_REPEAT_YES)
    assert cfg.kw_hit("เติมซ้ำได้", cfg.KW_REPEAT_YES)
    assert cfg.kw_hit("วันหมดอายุ", cfg.KW_EXPIRE)
    assert cfg.kw_hit("Code Expire Date", cfg.KW_EXPIRE)
    assert not cfg.kw_hit("ชื่อรางวัล", cfg.KW_EXPIRE)


# --------------------------------------------------------------- slugify
def test_slugify_basic():
    assert slugify("Summer Event Reward") == "summer-event-reward"
    assert slugify("  A/B  C  ") == "ab-c"


# ----------------------------------------------------------- shop draw rates
import item_finder


def test_a_plan_writes_odds_as_fractions_and_aztek_wants_percent():
    """A random box's rates add up to one in the plan; the site's field is a
    percentage. The real Cash Shop sheet's column is the case that matters."""
    soccer = ['0.1', 0.1, '0.12', 0.12, '0.12', 0.1, '0.1', 0.12, '0.12']
    assert item_finder._shop_rate_percent(soccer) == [
        '10', '10', '12', '12', '12', '10', '10', '12', '12']
    # Already a percentage — left alone.
    assert item_finder._shop_rate_percent(['25', '25', '50']) == ['25', '25', '50']


def test_a_rate_column_that_adds_up_to_neither_is_left_as_written():
    """Half a column cannot be told apart from percentages — 0.5 is a real
    half-percent odds. Guessing would silently multiply someone's rates by a
    hundred, so the values are passed through for the operator to read."""
    assert item_finder._shop_rate_percent(['0.1', '0.12']) == ['0.1', '0.12']
    assert item_finder._shop_rate_percent(['7', '9']) == ['7', '9']
    assert item_finder._shop_rate_percent(['', 'n/a', '1']) == ['', '', '100']


def test_a_product_with_draw_rates_is_marked_random():
    """The bundle has to be created as RANDOM, and the operator should not have
    to notice that themselves."""
    rows = [
        ['Item Kind', 'Item Name', 'Amt', 'Rate'],
        ['111', 'A', '1', 0.4],
        ['222', 'B', '1', 0.6],
    ]
    items = item_finder._shop_sheet_items(rows, 'Cash Shop 1.7')
    assert [it['rate'] for it in items] == ['40', '60']
    assert all(it['group_meta']['is_random'] for it in items)


def test_a_product_without_a_rate_column_stays_fixed():
    rows = [['Item Kind', 'Item Name', 'Amt'], ['111', 'A', '1']]
    items = item_finder._shop_sheet_items(rows, 'Cash Shop 1.7')
    assert 'rate' not in items[0]
    assert 'is_random' not in items[0]['group_meta']


# --------------------------------------------------------------- runner (ไม่มี pytest ก็รันได้)
if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); ok += 1; print("PASS", fn.__name__)
        except Exception:
            print("FAIL", fn.__name__)
            traceback.print_exc()
    print("\n%d/%d passed" % (ok, len(fns)))
    sys.exit(0 if ok == len(fns) else 1)
