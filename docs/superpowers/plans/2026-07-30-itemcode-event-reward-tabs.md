# Item Code Aztek Layout and Shared Reward Tabs Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to
> implement this plan task by task. Follow `superpowers:test-driven-development`
> for every behavior change and `superpowers:verification-before-completion`
> before reporting completion.

**Goal:** Reposition the Local Item Code editor into the approved Aztek-like
two-column layout and give the Item Code and Event editors accessible pill tabs
that show one reward set at a time without dropping inactive reward data.

**Architecture:** Keep both pages self-contained and preserve their existing
queue and payload schemas. Each page gets a page-local `activeRewardIndex`
presentation state. `renderSets()` owns tab normalization, tab rendering, and
the single active reward panel, while `jobFrom(entry)` continues to serialize
the complete `entry.rewards` array. The Item Code HTML gains semantic section
hooks and a responsive two-column wrapper; the existing Event section grid is
not moved.

**Tech Stack:** Static HTML/CSS, browser-side JavaScript, Python `pytest`, and
Playwright Chromium browser tests.

---

## Task 1: Lock the Item Code desktop and responsive layout with a browser test

**Files:**

- Modify: `tests/test_web_calendar_ui.py`
- Modify: `web/static/itemcodes.html:8-104`

### Step 1: Write the failing layout test

Add this test next to
`test_event_editor_uses_aztek_section_columns_and_collapses_on_small_screens`:

```python
def test_itemcode_editor_uses_aztek_columns_and_collapses_on_small_screens():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, ITEMCODES)
        page.evaluate("select(queue.add(blankCode()).key)")

        page.set_viewport_size({'width': 1400, 'height': 1000})
        desktop = page.evaluate("""
          () => {
            const general = document.querySelector(
              '[data-itemcode-section="general"]');
            const settings = document.querySelector(
              '[data-itemcode-section="settings"]');
            const rewards = document.querySelector(
              '[data-itemcode-section="rewards"]');
            return {
              generalLeft: general.getBoundingClientRect().left,
              generalRight: general.getBoundingClientRect().right,
              settingsLeft: settings.getBoundingClientRect().left,
              rewardsLeft: rewards.getBoundingClientRect().left
            };
          }
        """)
        assert abs(desktop['generalLeft'] - desktop['settingsLeft']) < 1
        assert desktop['rewardsLeft'] > desktop['generalRight']

        page.set_viewport_size({'width': 800, 'height': 1200})
        mobile = page.evaluate("""
          () => {
            const general = document.querySelector(
              '[data-itemcode-section="general"]');
            const settings = document.querySelector(
              '[data-itemcode-section="settings"]');
            const rewards = document.querySelector(
              '[data-itemcode-section="rewards"]');
            return {
              generalLeft: general.getBoundingClientRect().left,
              settingsLeft: settings.getBoundingClientRect().left,
              rewardsLeft: rewards.getBoundingClientRect().left,
              generalTop: general.getBoundingClientRect().top,
              settingsTop: settings.getBoundingClientRect().top,
              rewardsTop: rewards.getBoundingClientRect().top
            };
          }
        """)
        assert abs(mobile['generalLeft'] - mobile['settingsLeft']) < 1
        assert abs(mobile['generalLeft'] - mobile['rewardsLeft']) < 1
        assert mobile['generalTop'] < mobile['settingsTop'] < mobile['rewardsTop']
        browser.close()
```

The test uses independently measured bounding boxes rather than checking only
CSS class names.

### Step 2: Run the new test and confirm the intended failure

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "itemcode_editor_uses_aztek_columns"
```

Expected: FAIL because `data-itemcode-section` elements and the two-column
wrapper do not exist yet.

### Step 3: Implement the Item Code layout

In `web/static/itemcodes.html`, replace the editor's two full-width
`card-body section` blocks with one `card-body section` containing:

```html
<div class="itemcode-layout">
  <div class="itemcode-column">
    <section class="itemcode-panel" data-itemcode-section="general">
      <h3>ข้อมูลทั่วไป</h3>
      <div class="itemcode-fields">
        <!-- existing nameTh and nameEn labels -->
        <!-- existing slug label with class="full" -->
      </div>
    </section>
    <section class="itemcode-panel" data-itemcode-section="settings">
      <h3>ตั้งค่า</h3>
      <div class="itemcode-fields">
        <!-- existing kind, usesPerUser, startTime, and endTime labels -->
      </div>
    </section>
  </div>
  <div class="itemcode-column">
    <section class="itemcode-panel" data-itemcode-section="rewards">
      <!-- existing reward heading, count, add button, hint, and rsets -->
    </section>
  </div>
</div>
```

Move the existing controls without renaming or recreating their IDs. Add these
page-local styles, using existing console variables:

```css
.itemcode-layout{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:24px;align-items:start}
.itemcode-column{display:grid;gap:16px;min-width:0}
.itemcode-panel{border:1px solid var(--edge);border-radius:10px;
  background:var(--onyx);padding:16px;min-width:0}
.itemcode-panel h3{margin:0 0 14px;color:var(--ink)}
.itemcode-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px}
.itemcode-fields label{display:grid;gap:5px;font-size:12px;
  color:var(--muted);font-weight:600}
.itemcode-fields label.full{grid-column:1/-1}
.itemcode-fields input,.itemcode-fields select{width:100%}
@media(max-width:1100px){
  .itemcode-layout{grid-template-columns:1fr}
}
@media(max-width:650px){
  .itemcode-fields{grid-template-columns:1fr}
  .itemcode-fields label.full{grid-column:auto}
}
```

Keep `.formgrid` for dynamically generated reward card fields. Remove only the
obsolete Item Code comment that claims the whole editor is a four-column form.

### Step 4: Run the focused test and the existing Item Code regressions

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "itemcode_editor_uses_aztek_columns or itemcode_slug or locked_eligibility"
```

Expected: PASS.

### Step 5: Commit the layout slice

```powershell
git add web/static/itemcodes.html tests/test_web_calendar_ui.py
git commit -m "feat(itemcode): align editor layout with Aztek"
```

---

## Task 2: Add Item Code reward tabs without changing serialized rewards

**Files:**

- Modify: `tests/test_web_calendar_ui.py`
- Modify: `web/static/itemcodes.html:27-39`
- Modify: `web/static/itemcodes.html:145-312`

### Step 1: Write failing tests for tabs, payload preservation, add, remove, and queue reset

Add:

```python
def test_itemcode_reward_tabs_show_one_set_and_keep_all_sets_in_payload():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, ITEMCODES)
        page.evaluate("""
          addDrafts([{
            name_th: 'Two Sets',
            rewards: [
              {name_th: 'First Reward', name_en: 'First Reward'},
              {name_th: 'Second Reward', name_en: 'Second Reward'}
            ]
          }], 'test')
        """)

        tabs = page.locator('.reward-tab')
        assert tabs.all_text_contents() == ['1 ชุดที่ 1', '2 ชุดที่ 2']
        assert tabs.nth(0).get_attribute('aria-selected') == 'true'
        assert tabs.nth(1).get_attribute('aria-selected') == 'false'
        assert page.locator('#rsets .rset').count() == 1
        assert page.locator('#rsets input').first.input_value() == 'First Reward'

        tabs.nth(1).click()
        assert tabs.nth(0).get_attribute('aria-selected') == 'false'
        assert tabs.nth(1).get_attribute('aria-selected') == 'true'
        assert page.locator('#rsets .rset').count() == 1
        assert page.locator('#rsets input').first.input_value() == 'Second Reward'
        assert page.evaluate(
            "jobFrom(queue.current()).rewards.map(r => r.name_th)"
        ) == ['First Reward', 'Second Reward']
        browser.close()


def test_itemcode_reward_tabs_select_added_set_remove_safely_and_reset_per_queue():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, ITEMCODES)
        page.evaluate("""
          addDrafts([
            {name_th: 'First Code', rewards: [
              {name_th: 'First A'}, {name_th: 'First B'}
            ]},
            {name_th: 'Second Code', rewards: [
              {name_th: 'Second A'}, {name_th: 'Second B'}
            ]}
          ], 'test')
        """)

        page.locator('.reward-tab').nth(1).click()
        page.locator('#btnAddSet').click()
        tabs = page.locator('.reward-tab')
        assert tabs.all_text_contents() == [
            '1 ชุดที่ 1', '2 ชุดที่ 2', '3 ชุดที่ 3']
        assert tabs.nth(2).get_attribute('aria-selected') == 'true'

        page.locator('#rsets .rset .danger').click()
        tabs = page.locator('.reward-tab')
        assert tabs.count() == 2
        assert tabs.nth(1).get_attribute('aria-selected') == 'true'

        page.locator('#queuePick').select_option(
            page.evaluate("queue.items[1].key"))
        assert page.locator('.reward-tab').nth(0).get_attribute(
            'aria-selected') == 'true'
        assert page.locator('#rsets input').first.input_value() == 'Second A'
        browser.close()
```

### Step 2: Run the new Item Code tab tests and confirm the intended failures

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "itemcode_reward_tabs"
```

Expected: FAIL because `.reward-tab` does not exist and all `.rset` cards are
currently rendered.

### Step 3: Implement page-local active reward state and accessible tabs

In the Item Code script, add directly after `pendingGame`:

```javascript
let activeRewardIndex = 0;
```

In `select(key)`, reset `activeRewardIndex = 0` before `renderSets()`.

Replace `renderSets()` with logic that:

1. Clears `#rsets`.
2. Returns early if there is no current queue entry.
3. Clamps `activeRewardIndex` to
   `0..entry.rewards.length - 1`.
4. Updates `#rsetCount`.
5. Builds one `.reward-tabs` element with `role="tablist"` and
   `aria-label="ชุดรางวัล"`.
6. Builds one button per reward with class `.reward-tab`, exact text
   `` `${index + 1} ชุดที่ ${index + 1}` ``, `role="tab"`, unique `id`,
   `aria-selected`, and `aria-controls`.
7. On tab click, assigns `activeRewardIndex = index` and calls `renderSets()`.
8. Appends only `setCard(entry, entry.rewards[activeRewardIndex],
   activeRewardIndex)`.
9. Gives the active `.rset` `role="tabpanel"`, a matching panel ID, and
   `aria-labelledby` pointing at its tab.

Use IDs derived only from the safe numeric active index, for example
`itemcode-reward-tab-2` and `itemcode-reward-panel-2`; only one queue entry is
rendered at a time.

Update add behavior to select the appended set:

```javascript
entry.rewards.push(blankReward(''));
activeRewardIndex = entry.rewards.length - 1;
queue.save();
renderSets();
renderQueue();
```

Update remove behavior after `splice(index, 1)`:

```javascript
activeRewardIndex = Math.min(index, entry.rewards.length - 1);
```

This selects the next reward that shifted into the removed index, or the
previous reward when the removed reward was last. Keep the existing
one-reward warning unchanged.

Add:

```css
.reward-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 14px}
.reward-tab{border:1px solid var(--edge);border-radius:999px;
  background:transparent;color:var(--ink);padding:8px 14px}
.reward-tab[aria-selected="true"]{border-color:var(--arc);
  background:var(--arc);color:#fff}
.reward-tab:focus-visible{outline:2px solid var(--arc-bright);
  outline-offset:2px}
```

Do not put `activeRewardIndex` on the entry, in local storage, or in
`jobFrom(entry)`.

### Step 4: Run the Item Code tab tests and related import/payload tests

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "itemcode_reward_tabs or imported_itemcode or itemcode_slug"
```

Expected: PASS.

### Step 5: Commit the Item Code tab slice

```powershell
git add web/static/itemcodes.html tests/test_web_calendar_ui.py
git commit -m "feat(itemcode): show reward sets as tabs"
```

---

## Task 3: Give Event the same reward tab contract without moving Event sections

**Files:**

- Modify: `tests/test_web_calendar_ui.py`
- Modify: `web/static/events.html:8-51`
- Modify: `web/static/events.html:186-353`

### Step 1: Write failing Event tab and payload tests

Add:

```python
def test_event_reward_tabs_show_one_set_and_keep_all_sets_in_payload():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, EVENTS)
        page.evaluate("""
          addDrafts([{
            name_th: 'Two Set Event',
            rewards: [
              {name_th: 'First Prize', name_en: 'First Prize'},
              {name_th: 'Second Prize', name_en: 'Second Prize'}
            ]
          }], 'test')
        """)

        tabs = page.locator('.reward-tab')
        assert tabs.all_text_contents() == ['1 ชุดที่ 1', '2 ชุดที่ 2']
        assert tabs.nth(0).get_attribute('aria-selected') == 'true'
        assert tabs.nth(1).get_attribute('aria-selected') == 'false'
        assert page.locator('#rsets .rset').count() == 1
        assert page.locator('#rsets input').first.input_value() == 'First Prize'

        tabs.nth(1).click()
        assert tabs.nth(1).get_attribute('aria-selected') == 'true'
        assert page.locator('#rsets input').first.input_value() == 'Second Prize'
        assert page.evaluate(
            "jobFrom(queue.current()).rewards.map(r => r.name_th)"
        ) == ['First Prize', 'Second Prize']
        browser.close()


def test_event_reward_tabs_select_added_set_remove_safely_and_reset_per_queue():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = _tool_page(browser, EVENTS)
        page.evaluate("""
          addDrafts([
            {name_th: 'First Event', rewards: [
              {name_th: 'First A'}, {name_th: 'First B'}
            ]},
            {name_th: 'Second Event', rewards: [
              {name_th: 'Second A'}, {name_th: 'Second B'}
            ]}
          ], 'test')
        """)

        page.locator('.reward-tab').nth(1).click()
        page.locator('#btnAddSet').click()
        tabs = page.locator('.reward-tab')
        assert tabs.nth(2).get_attribute('aria-selected') == 'true'

        page.locator('#rsets .rset .danger').click()
        tabs = page.locator('.reward-tab')
        assert tabs.count() == 2
        assert tabs.nth(1).get_attribute('aria-selected') == 'true'

        page.locator('#queuePick').select_option(
            page.evaluate("queue.items[1].key"))
        assert page.locator('.reward-tab').nth(0).get_attribute(
            'aria-selected') == 'true'
        assert page.locator('#rsets input').first.input_value() == 'Second A'
        browser.close()
```

### Step 2: Run the Event tab tests and confirm the intended failures

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "event_reward_tabs"
```

Expected: FAIL because Event still renders all reward cards and has no tab
buttons.

### Step 3: Implement the same Event tab behavior locally

Apply the same `activeRewardIndex`, `select()`, `renderSets()`, add, remove,
tab ARIA, and `.reward-tabs` / `.reward-tab` CSS rules from Task 2 to
`web/static/events.html`, using the Event-specific ID prefixes
`event-reward-tab-` and `event-reward-panel-`.

Do not move or rename any of these existing sections:

- `data-event-section="general"`
- `data-event-section="rewards"`
- `data-event-section="claim-rules"`
- `data-event-section="activity-window"`
- `data-event-section="claim-window"`

Do not change Event draft fields, Bundle handoff matching, claim-window
mirroring, or `jobFrom(entry)`.

### Step 4: Run Event tab and existing Event layout/data regressions

Run:

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider -k "event_reward_tabs or event_editor_uses_aztek or event_page_imports or event_bundle_ids or claim_window"
```

Expected: PASS.

### Step 5: Commit the Event tab slice

```powershell
git add web/static/events.html tests/test_web_calendar_ui.py
git commit -m "feat(event): show reward sets as tabs"
```

---

## Task 4: Verify the combined UI and guard against regressions

**Files:**

- Verify: `web/static/itemcodes.html`
- Verify: `web/static/events.html`
- Verify: `tests/test_web_calendar_ui.py`

### Step 1: Run the complete browser UI test module

```powershell
python -m pytest tests/test_web_calendar_ui.py -q -p no:cacheprovider
```

Expected: PASS.

### Step 2: Run the complete automated suite with an isolated temp directory

```powershell
python -m pytest tests -q --basetemp C:\tmp\afc-itemcode-event-tabs-verify -p no:cacheprovider
```

Expected: all tests PASS.

### Step 3: Perform local visual verification only

Open the Local Item Code and Event pages at desktop width and verify:

- Item Code general/settings are left and rewards are right.
- Item Code collapses to general, settings, rewards at `800px`.
- Both pages show the exact tab labels `1 ชุดที่ 1`, `2 ชุดที่ 2`.
- The selected tab uses the filled accent pill.
- Only the selected reward form is visible.
- Long tab rows wrap without horizontal page scrolling.
- Existing Event section placement is unchanged.
- Date/time inputs still display a space rather than `T`.

Use only Local drafts. Do not click either real-create button and do not create
an Item Code or Event on Aztek.

### Step 4: Review the final diff for scope and persistence leaks

Run:

```powershell
git diff HEAD~3 -- web/static/itemcodes.html web/static/events.html tests/test_web_calendar_ui.py
rg -n "activeRewardIndex|reward-tab|data-itemcode-section" web/static/itemcodes.html web/static/events.html tests/test_web_calendar_ui.py
git status --short
```

Confirm:

- No backend or payload schema file changed.
- `activeRewardIndex` appears only as page-local JavaScript state.
- `jobFrom(entry)` still returns every `entry.rewards` item.
- No generated files, database files, uploaded workbooks, screenshots,
  browser profiles, or secrets are staged.

### Step 5: Report the verified result without publishing

Report test counts and the three implementation commits. Do not push, build an
installer, or publish a GitHub Release until the user explicitly asks for that
separate action.
