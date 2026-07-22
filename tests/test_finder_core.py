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

def test_build_launch_kwargs_with_chrome():
    kw = fc.build_launch_kwargs(headless=False, user_data_dir='C:/prof', chrome_exe='C:/chrome.exe')
    check('user_data_dir set', kw['user_data_dir'] == 'C:/prof')
    check('headless False', kw['headless'] is False)
    check('args maximized', kw['args'] == ['--start-maximized'])
    check('no_viewport True', kw['no_viewport'] is True)
    check('executable_path set', kw['executable_path'] == 'C:/chrome.exe')

def test_build_launch_kwargs_no_chrome():
    kw = fc.build_launch_kwargs(headless=True, user_data_dir='C:/prof')
    check('headless True', kw['headless'] is True)
    check('no executable_path key when chrome_exe None', 'executable_path' not in kw)

def test_launch_kwargs_match_legacy_shapes():
    # _auto: headless from config, profile dir, chrome_exe present
    legacy_auto = dict(user_data_dir='PROF', headless=True,
                       args=['--start-maximized'], no_viewport=True)
    legacy_auto['executable_path'] = 'CHROME'
    check('_auto shape matches',
          fc.build_launch_kwargs(headless=True, user_data_dir='PROF', chrome_exe='CHROME') == legacy_auto)
    # _open_login: headless False, no chrome_exe
    legacy_login = dict(user_data_dir='PROF', headless=False,
                        args=['--start-maximized'], no_viewport=True)
    check('_open_login shape matches',
          fc.build_launch_kwargs(headless=False, user_data_dir='PROF') == legacy_login)

if __name__ == '__main__':
    test_searchconfig_from_dict_roundtrip()
    test_searchconfig_defaults()
    test_build_launch_kwargs_with_chrome()
    test_build_launch_kwargs_no_chrome()
    test_launch_kwargs_match_legacy_shapes()
    print('\n' + ('ALL PASS' if not FAIL else 'FAIL: ' + ', '.join(FAIL)))
    sys.exit(1 if FAIL else 0)
