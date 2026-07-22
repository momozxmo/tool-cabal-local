# Item Finder Core Extraction (Phase 1 — Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a GUI-free `finder_core` module and move the browser-launch + search-config plumbing into it behind tests, so the future web backend and the existing desktop app share one seam — without changing any desktop behavior.

**Architecture:** Create a new `finder_core.py` with zero tkinter imports. It holds (a) a `SearchConfig` dataclass mirroring the `data` dict that `item_finder.App._start` already builds, and (b) a pure `build_launch_kwargs()` helper that both `App._auto` and `App._open_login` currently inline. Desktop code is rewired to call these — same behavior, now DRY and unit-tested. This is the first, spike-independent step of separating the automation core from the GUI (spec §6).

**Tech Stack:** Python 3.12, dataclasses, Playwright (existing), no new dependencies. Tests are plain-assert scripts runnable with `python tests/<file>.py`, matching the existing `tests/test_pure.py` convention.

## Global Constraints

- Python 3.12; Windows dev host (paths use the repo root `C:\Users\koomo\Documents\Crazy\all for cabal`).
- `finder_core.py` MUST NOT import `tkinter` (it is the GUI-free seam — the whole point of this plan).
- No new third-party dependencies in this plan.
- Desktop app behavior MUST stay byte-for-byte identical: the Playwright launch kwargs produced after the refactor must equal those produced before.
- Match the existing test style (`tests/test_pure.py`: plain `assert` + a `__main__` runner that prints `PASS`/`FAIL` and exits non-zero on failure). Do NOT introduce pytest as a requirement.
- Existing regression scripts must still pass: `python tests/test_pure.py`.
- Follow existing code style in `item_finder.py` (module-level helpers, Thai comments where the surrounding code uses them).

---

### Task 1: `SearchConfig` dataclass in `finder_core.py`

**Files:**
- Create: `finder_core.py`
- Test: `tests/test_finder_core.py`

**Interfaces:**
- Consumes: nothing (new module).
- Produces:
  - `finder_core.SearchConfig` — a frozen dataclass with fields:
    `game: str`, `url: str`, `multi: list`, `deep: bool = False`, `web: str = 'any'`,
    `img: str = 'any'`, `qty_val: str = ''`, `trade: str = 'any'`, `drill: str = 'any'`,
    `crit_val: str = ''`, `batch: int = 10`, `headless: bool = False`, `read_desc: bool = False`.
  - `SearchConfig.from_dict(d: dict) -> SearchConfig` — build from the exact `data` dict that
    `item_finder.App._start` produces (keys: game, url, multi, deep, web, img, qty_val, trade,
    drill, crit_val, batch, headless, read_desc). Unknown keys are ignored.
  - `SearchConfig.as_dict() -> dict` — round-trips back to a plain dict with those same keys.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finder_core.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_finder_core.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'finder_core'`

- [ ] **Step 3: Write minimal implementation**

Create `finder_core.py`:

```python
# -*- coding: utf-8 -*-
"""GUI-free core ของ Item Finder — ห้าม import tkinter (ใช้ร่วมทั้ง desktop และ web backend)."""
from dataclasses import dataclass, field, asdict

_CONFIG_KEYS = ('game', 'url', 'multi', 'deep', 'web', 'img', 'qty_val',
                'trade', 'drill', 'crit_val', 'batch', 'headless', 'read_desc')


@dataclass(frozen=True)
class SearchConfig:
    game: str
    url: str
    multi: list
    deep: bool = False
    web: str = 'any'
    img: str = 'any'
    qty_val: str = ''
    trade: str = 'any'
    drill: str = 'any'
    crit_val: str = ''
    batch: int = 10
    headless: bool = False
    read_desc: bool = False

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d[k] for k in _CONFIG_KEYS if k in d})

    def as_dict(self):
        return {k: getattr(self, k) for k in _CONFIG_KEYS}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_finder_core.py`
Expected: `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add finder_core.py tests/test_finder_core.py
git commit -m "feat(finder_core): add SearchConfig dataclass mirroring the search data dict"
```

---

### Task 2: `build_launch_kwargs()` in `finder_core.py`

**Files:**
- Modify: `finder_core.py`
- Test: `tests/test_finder_core.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `finder_core.build_launch_kwargs(*, headless: bool, user_data_dir: str, chrome_exe: str | None = None) -> dict`
    — returns the exact kwargs dict currently inlined in `item_finder.App._auto` /
    `App._open_login`:
    `{'user_data_dir': user_data_dir, 'headless': headless, 'args': ['--start-maximized'], 'no_viewport': True}`
    plus `'executable_path': chrome_exe` only when `chrome_exe` is truthy.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_finder_core.py` (add these functions and add their calls in `__main__`):

```python
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
```

Update the `__main__` block to also call `test_build_launch_kwargs_with_chrome()` and
`test_build_launch_kwargs_no_chrome()` before the summary print.

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_finder_core.py`
Expected: FAIL — `AttributeError: module 'finder_core' has no attribute 'build_launch_kwargs'`

- [ ] **Step 3: Write minimal implementation**

Append to `finder_core.py`:

```python
def build_launch_kwargs(*, headless, user_data_dir, chrome_exe=None):
    """kwargs สำหรับ launch_persistent_context — ให้ตรงกับที่ _auto/_open_login เคย inline ไว้."""
    kw = dict(user_data_dir=user_data_dir, headless=headless,
              args=['--start-maximized'], no_viewport=True)
    if chrome_exe:
        kw['executable_path'] = chrome_exe
    return kw
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_finder_core.py`
Expected: `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add finder_core.py tests/test_finder_core.py
git commit -m "feat(finder_core): add build_launch_kwargs helper"
```

---

### Task 3: Rewire desktop `_auto` and `_open_login` to use `build_launch_kwargs`

**Files:**
- Modify: `item_finder.py` (method `_auto`, around the `kw = dict(user_data_dir=CHROME_PROFILE, headless=data['headless'], ...)` block; and method `_open_login`, the `kw = dict(user_data_dir=CHROME_PROFILE, headless=False, ...)` block)
- Test: `tests/test_finder_core.py`

**Interfaces:**
- Consumes: `finder_core.build_launch_kwargs` (Task 2).
- Produces: no new public interface; desktop now delegates launch-kwargs construction to `finder_core`.

**Context — current code (verify before editing; line numbers may drift):**
`_auto` currently builds:
```python
kw = dict(user_data_dir=CHROME_PROFILE, headless=data['headless'],
          args=['--start-maximized'], no_viewport=True)
if chrome_exe:
    kw['executable_path'] = chrome_exe
```
`_open_login` currently builds the same shape with `headless=False`.

- [ ] **Step 1: Write the failing test (parity guard)**

Append to `tests/test_finder_core.py` a test proving the helper reproduces the exact legacy kwargs
for both call sites, so the rewire cannot drift:

```python
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
```

Add `test_launch_kwargs_match_legacy_shapes()` to the `__main__` runner.

- [ ] **Step 2: Run test to verify it passes (helper already correct)**

Run: `python tests/test_finder_core.py`
Expected: `ALL PASS` (this test guards the shape the rewire must preserve).

- [ ] **Step 3: Add the import and rewire `_auto`**

In `item_finder.py`, confirm the top-of-file imports include the local modules (it already has
`import aztek_core as core`). Add near those imports:
```python
import finder_core
```

Replace the `_auto` kwargs block:
```python
kw = dict(user_data_dir=CHROME_PROFILE, headless=data['headless'],
          args=['--start-maximized'], no_viewport=True)
if chrome_exe:
    kw['executable_path'] = chrome_exe
```
with:
```python
kw = finder_core.build_launch_kwargs(headless=data['headless'],
                                     user_data_dir=CHROME_PROFILE, chrome_exe=chrome_exe)
```

- [ ] **Step 4: Rewire `_open_login`**

In `item_finder.py` `_open_login`, replace:
```python
kw = dict(user_data_dir=CHROME_PROFILE, headless=False,
          args=['--start-maximized'], no_viewport=True)
if chrome_exe:
    kw['executable_path'] = chrome_exe
```
with:
```python
kw = finder_core.build_launch_kwargs(headless=False,
                                     user_data_dir=CHROME_PROFILE, chrome_exe=chrome_exe)
```

- [ ] **Step 5: Verify compile + full regression**

Run: `python -c "import py_compile; py_compile.compile('item_finder.py', doraise=True); py_compile.compile('finder_core.py', doraise=True); print('COMPILE OK')"`
Expected: `COMPILE OK`

Run: `python tests/test_finder_core.py`
Expected: `ALL PASS`

Run: `python tests/test_pure.py`
Expected: existing suite still passes (unchanged behavior).

- [ ] **Step 6: Commit**

```bash
git add item_finder.py
git commit -m "refactor(item_finder): use finder_core.build_launch_kwargs in _auto/_open_login"
```

---

## Subsequent plans (decomposition roadmap — NOT part of this plan)

This plan is Phase 1's foundation only. The remaining work is separate plans, each producing
working, testable software, written after the one before it lands:

1. **Phase 0 spike (do first, in parallel — no plan doc needed):** Run the EXISTING desktop Item
   Finder against aztek with the "Headless (ซ่อน browser)" checkbox ON. If a normal search still
   returns correct results, headless-on-free-tier is validated. If aztek blocks headless, decide
   host/mode before investing further (spec §13). This is ~15 min with code that already exists.
2. **Phase 1b — extract the async search engine:** move `_search_all`, `_check_item_detail`,
   `_read_all_pages`, `_apply_filters`, `_wait_table_ready`, `_go_back`, `_wait_detail_ready` into
   `finder_core`, replacing `self.log`→`log_cb`, `self._cancel`→`should_cancel()`,
   `self.add_result_row`/`self._results.append`→`on_result(item)`, `self.set_progress`→`progress_cb`,
   and adding `storage_state` support to the browser launch. Rewire desktop `App` to pass its GUI
   methods as callbacks (desktop parity). Test with a mock `page` (reuse the `verify_*.py` pattern).
3. **Phase 2 — backend skeleton:** FastAPI + DB schema (Supabase/Neon) + app auth + tool registry.
4. **Phase 3 — browser extension + session import/store (encrypted).**
5. **Phase 4 — job queue + Playwright worker + WebSocket progress** (worker calls `finder_core`).
6. **Phase 5 — frontend (Item Finder page) + templates + audit + admin.**
7. **Phase 6 — deploy (Docker → Render + Supabase/Neon) + e2e.**
