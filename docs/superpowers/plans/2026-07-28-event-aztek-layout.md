# Event Aztek Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Event editor follow Aztek v2's two-column section placement, name a single reward set after its Event, and keep visible claim dates free of the `T` separator.

**Architecture:** Keep Event draft semantics in `web/event_plan.py` and keep presentation behavior in `web/static/events.html`. Preserve every existing field ID and API payload so `web/event_runner.py` remains unchanged; use focused pure-Python and Playwright regression tests to pin the new behavior.

**Tech Stack:** Python 3, FastAPI project modules, vanilla HTML/CSS/JavaScript, pytest, Playwright.

## Global Constraints

- Reorganize only the Event editor; keep queue, import, preview/create, results, and log behavior unchanged.
- Do not add Aztek Details or Status fields.
- Do not create real Aztek records during implementation or verification.
- Preserve the existing Item Code changes in `web/itemcode_plan.py` and `tests/test_web_itemcode_plan.py`.
- Use `YYYY-MM-DD HH:MM:SS` for all visible Event date fields.

---

### Task 1: Single Reward Set Naming

**Files:**
- Modify: `web/event_plan.py:84-121`
- Test: `tests/test_web_event_plan.py:31-42`

**Interfaces:**
- Consumes: `build_event_draft(sheet_name: str, event: dict, game: str, now: datetime | None) -> dict`
- Produces: the existing draft shape, with `rewards[0].name_th` and `rewards[0].name_en` equal to the Event name only when there is exactly one reward.

- [ ] **Step 1: Write the failing single-reward naming test**

```python
def test_a_single_reward_set_uses_the_event_name():
    draft = event_plan.build_event_drafts([
        ('Activity A', _event(
            name='Summer Event',
            rewards=[{'name': 'WINNER REWARDS', 'items': [{'kind': '1'}]}],
        )),
    ], TH, now=NOW)[0]

    reward = draft['rewards'][0]
    assert (reward['name_th'], reward['name_en']) == (
        'Summer Event', 'Summer Event')
    assert reward['group'] == 'WINNER REWARDS'
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest tests/test_web_event_plan.py::test_a_single_reward_set_uses_the_event_name -q -p no:cacheprovider
```

Expected: FAIL because both reward names are currently `WINNER REWARDS`.

- [ ] **Step 3: Write the failing multi-reward preservation test**

```python
def test_multiple_reward_sets_keep_their_document_names():
    draft = event_plan.build_event_drafts(
        [('Activity A', _event())], TH, now=NOW)[0]

    assert [reward['name_th'] for reward in draft['rewards']] == [
        'Lucky Draw', 'Participation']
```

- [ ] **Step 4: Run the naming tests**

Run:

```powershell
python -m pytest tests/test_web_event_plan.py -q -p no:cacheprovider
```

Expected: the single-reward test fails and the existing multi-reward behavior passes.

- [ ] **Step 5: Apply the minimal naming rule**

After the reward loop in `build_event_draft`, add:

```python
if len(rewards) == 1 and name:
    rewards[0]['name_th'] = name
    rewards[0]['name_en'] = name
```

Do not change `group` or `group_key`; Bundle handoff identity still relies on them.

- [ ] **Step 6: Run the Event-plan tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_web_event_plan.py -q -p no:cacheprovider
```

Expected: all tests in the file pass.

---

### Task 2: Claim Window Display Without `T`

**Files:**
- Modify: `web/static/events.html:192-197`
- Test: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Consumes: shared `displayStamp(text: string) -> string` from `web/static/console.js`
- Produces: `mirrorWindow(entry)` that stores the source values unchanged but always formats the two visible claim inputs.

- [ ] **Step 1: Write the failing mirror-window browser test**

```python
def test_event_claim_window_keeps_a_space_when_it_is_mirrored():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, EVENTS)
        page.evaluate("""
          addDrafts([{
            name_th: 'Summer Event',
            start_event: '2026-07-28T00:00:00',
            end_event: '2026-08-31T22:59:59',
            start_claim: '',
            end_claim: '',
            same_window: false,
            rewards: [{name_th: 'Summer Event', name_en: 'Summer Event'}]
          }], 'test')
        """)

        page.locator('#sameWindow').check()

        assert page.locator('#startClaim').input_value() == \
            '2026-07-28 00:00:00'
        assert page.locator('#endClaim').input_value() == \
            '2026-08-31 22:59:59'
        browser.close()
```

- [ ] **Step 2: Run the focused browser test and verify RED**

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py::test_event_claim_window_keeps_a_space_when_it_is_mirrored -q -p no:cacheprovider
```

Expected: FAIL because `mirrorWindow` writes the stored `T` values directly into the visible inputs.

- [ ] **Step 3: Format both mirrored values**

Change only the visible assignments:

```javascript
$('startClaim').value = displayStamp(entry.start_claim);
$('endClaim').value = displayStamp(entry.end_claim);
```

Keep `entry.start_claim` and `entry.end_claim` equal to their activity-window source values so the existing payload logic remains compatible.

- [ ] **Step 4: Run the calendar UI tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider
```

Expected: all calendar UI tests pass.

---

### Task 3: Aztek-Aligned Event Editor Layout

**Files:**
- Modify: `web/static/events.html:9-112`
- Test: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Produces: `.event-layout`, `.event-column`, and `[data-event-section]` presentation hooks.
- Preserves: all existing element IDs consumed by the inline Event JavaScript and all fields consumed by `jobFrom(entry)`.

- [ ] **Step 1: Write the failing section-placement browser test**

```python
def test_event_editor_uses_aztek_section_columns_and_collapses_on_small_screens():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, EVENTS)
        page.evaluate("select(queue.add(blankEvent()).key)")

        page.set_viewport_size({'width': 1400, 'height': 1000})
        desktop = page.evaluate("""
          () => {
            const layout = document.querySelector('.event-layout');
            const general = document.querySelector('[data-event-section="general"]');
            const activity = document.querySelector('[data-event-section="activity-window"]');
            return {
              columns: getComputedStyle(layout).gridTemplateColumns,
              generalLeft: general.getBoundingClientRect().left,
              generalRight: general.getBoundingClientRect().right,
              activityLeft: activity.getBoundingClientRect().left
            };
          }
        """)
        assert desktop['activityLeft'] > desktop['generalRight']

        page.set_viewport_size({'width': 800, 'height': 1200})
        mobile = page.evaluate("""
          () => {
            const general = document.querySelector('[data-event-section="general"]');
            const activity = document.querySelector('[data-event-section="activity-window"]');
            return {
              generalLeft: general.getBoundingClientRect().left,
              activityLeft: activity.getBoundingClientRect().left
            };
          }
        """)
        assert abs(mobile['generalLeft'] - mobile['activityLeft']) < 1
        browser.close()
```

- [ ] **Step 2: Run the focused layout test and verify RED**

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py::test_event_editor_uses_aztek_section_columns_and_collapses_on_small_screens -q -p no:cacheprovider
```

Expected: FAIL because the Event editor has no `.event-layout` or section hooks.

- [ ] **Step 3: Reorganize the existing fields without renaming IDs**

Create this section order:

```html
<div class="event-layout">
  <div class="event-column">
    <section class="event-panel" data-event-section="general">...</section>
    <section class="event-panel" data-event-section="rewards">...</section>
    <section class="event-panel" data-event-section="claim-rules">...</section>
  </div>
  <aside class="event-column">
    <section class="event-panel" data-event-section="activity-window">...</section>
    <section class="event-panel" data-event-section="claim-window">...</section>
  </aside>
</div>
```

Move existing controls only. Keep `planWarnings` immediately above
`.event-layout`, and keep every ID from `FIELDS`, `sameWindow`, `rsets`,
`rsetCount`, and `btnAddSet`.

- [ ] **Step 4: Add the responsive layout styles**

```css
.event-layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(320px,1fr);
  gap:24px;align-items:start}
.event-column{display:grid;gap:16px;min-width:0}
.event-panel{border:1px solid var(--edge);border-radius:10px;
  background:var(--onyx);padding:16px;min-width:0}
.event-panel h3{margin:0 0 14px;font-size:15px}
@media(max-width:1100px){
  .event-layout{grid-template-columns:1fr}
}
```

Retain the existing `.formgrid` responsive behavior inside each panel.

- [ ] **Step 5: Run the Event browser tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider
```

Expected: all tests in the file pass.

---

### Task 4: Full Regression Verification

**Files:**
- Verify only; no new production files.

**Interfaces:**
- Confirms the Event changes coexist with Item Code, Bundle, auth/local mode,
  and browser automation behavior.

- [ ] **Step 1: Inspect the final diff**

Run:

```powershell
git diff --check
git diff -- web/event_plan.py web/static/events.html tests/test_web_event_plan.py tests/test_web_calendar_ui.py
git status --short
```

Expected: no whitespace errors; only the intended Event files plus the
pre-existing Item Code modifications are present.

- [ ] **Step 2: Run all tests**

Run from an unrestricted test process because the Playwright suite must spawn
Chromium:

```powershell
python -m pytest tests -q --basetemp C:\tmp\afc-event-layout-verify -p no:cacheprovider
```

Expected: the complete suite passes with zero failures.

- [ ] **Step 3: Report without publishing**

Report the exact test count, changed files, and the source-only status. Do not
commit the implementation, push, rebuild the installer, publish a release, or
create an Aztek Event unless the user asks separately.
