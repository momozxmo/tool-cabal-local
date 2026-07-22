# -*- coding: utf-8 -*-
import os, sys
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import finder_core as fc

FAIL = []
def check(name, cond):
    print(('PASS ' if cond else '*** FAIL *** ') + name)
    if not cond:
        FAIL.append(name)

def test_searchconfig_from_dict_roundtrip():
    d = {'game': 'CabalPC SEA', 'url': 'http://x', 'multi': [{'kind': '1'}],
         'deep': True, 'web': 'yes', 'img': 'any', 'qty_val': '5', 'trade': 'no',
         'drill': 'any', 'crit_val': '', 'batch': 10, 'headless': True, 'read_desc': True}
    cfg = fc.SearchConfig.from_dict(d)
    check('from_dict keeps game', cfg.game == 'CabalPC SEA')
    check('from_dict keeps deep', cfg.deep is True)
    check('from_dict keeps headless', cfg.headless is True)
    check('from_dict keeps read_desc', cfg.read_desc is True)
    check('as_dict round-trips', cfg.as_dict() == d)

def test_searchconfig_defaults():
    cfg = fc.SearchConfig.from_dict({'game': 'g', 'url': 'u', 'multi': []})
    check('default deep False', cfg.deep is False)
    check('default web any', cfg.web == 'any')
    check('default batch 10', cfg.batch == 10)
    check('unknown keys ignored', fc.SearchConfig.from_dict(
        {'game': 'g', 'url': 'u', 'multi': [], 'bogus': 1}).game == 'g')

if __name__ == '__main__':
    test_searchconfig_from_dict_roundtrip()
    test_searchconfig_defaults()
    print('\n' + ('ALL PASS' if not FAIL else 'FAIL: ' + ', '.join(FAIL)))
    sys.exit(1 if FAIL else 0)
