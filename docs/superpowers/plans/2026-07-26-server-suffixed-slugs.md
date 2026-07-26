# Server-suffixed Slugs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append the selected Cabal server code to every slug generated or filled automatically by the Item Code and Event web pages.

**Architecture:** Put the game-to-suffix rule in the shared `console.js` code so both pages use one implementation. Call that helper only at automatic-generation boundaries; ordinary slug-field input and game changes never rewrite an operator's manual value.

**Tech Stack:** Vanilla JavaScript, HTML, Playwright browser tests under pytest.

## Global Constraints

- `CabalM TH` → `mth`, `CabalM SEA` → `msea`, `CabalPC TH` → `pcth`, and `CabalPC SEA` → `pcsea`.
- An existing selected-server suffix must not be duplicated.
- Manual edits to the slug field must remain unchanged.
- No live Item Code or Event may be saved during verification.
- Preserve the uncommitted calendar-close fix and its regression test.

---

### Task 1: Shared server-aware slug generator

**Files:**
- Modify: `web/static/console.js`
- Modify: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Consumes: `slugify(text: unknown): string`
- Produces: `slugForGame(text: unknown, game: unknown): string`

- [ ] **Step 1: Write the failing browser test**

Add a real-browser assertion after loading `console.js`:

```python
def test_generated_slugs_end_with_the_selected_server_without_duplicates():
    with _shared_console_page() as page:
        assert page.evaluate("slugForGame('Summer Event', 'CabalM TH')") == 'summer-event-mth'
        assert page.evaluate("slugForGame('Summer Event', 'CabalM SEA')") == 'summer-event-msea'
        assert page.evaluate("slugForGame('Summer Event', 'CabalPC TH')") == 'summer-event-pcth'
        assert page.evaluate("slugForGame('Summer Event', 'CabalPC SEA')") == 'summer-event-pcsea'
        assert page.evaluate(
            "slugForGame('summer-event-msea', 'CabalM SEA')"
        ) == 'summer-event-msea'
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider tests\test_web_calendar_ui.py -q
```

Expected: failure because `slugForGame` is not defined.

- [ ] **Step 3: Implement the shared helper**

Add to `console.js` immediately after `slugify`:

```javascript
const SERVER_SUFFIX = Object.freeze({
  'CabalM TH': 'mth',
  'CabalM SEA': 'msea',
  'CabalPC TH': 'pcth',
  'CabalPC SEA': 'pcsea',
});

function slugForGame(text, game) {
  const made = slugify(text);
  const suffix = SERVER_SUFFIX[String(game || '').trim()] || '';
  if (!made || !suffix || made.endsWith(`-${suffix}`)) return made;
  return `${made}-${suffix}`;
}
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all calendar/slug browser tests pass.

---

### Task 2: Wire automatic Item Code slug paths

**Files:**
- Modify: `web/static/itemcodes.html`
- Modify: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Consumes: `slugForGame(text, game)` from Task 1
- Produces: server-suffixed slugs from **สร้างให้**, `addDrafts`, and `drainHandoff`

- [ ] **Step 1: Add failing browser coverage for the real page**

Inline the real shared script into the real Item Code HTML in a Playwright page.
Set the game to `CabalPC TH`, type `Summer Event` in `#nameEn`, click
`#btnSlug`, and assert `#slug` equals `summer-event-pcth`. Then set
`#slug` to `operator-choice`, dispatch `input`, change the game to
`CabalM SEA`, and assert the value remains `operator-choice`.

Call `addDrafts([{name_th: 'Imported', slug: 'imported-code'}], 'test')`
with `CabalM SEA` selected and assert the active queue entry's slug is
`imported-code-msea`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider tests\test_web_calendar_ui.py -q
```

Expected: button/import assertions receive unsuffixed slugs.

- [ ] **Step 3: Apply the helper only to automatic paths**

Use:

```javascript
slugForGame($('nameEn').value || $('nameTh').value, $('game').value)
```

inside `btnSlug`; normalize `entry.slug` inside `addDrafts` with
`pendingGame || $('game').value`; and generate handoff slugs with
`payload.game || $('game').value`. Do not add a game-change handler that edits
the slug field.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all focused tests pass.

---

### Task 3: Wire Event generation and verify the project

**Files:**
- Modify: `web/static/events.html`
- Modify: `tests/test_web_calendar_ui.py`

**Interfaces:**
- Consumes: `slugForGame(text, game)` from Task 1
- Produces: server-suffixed Event slugs from **สร้างให้**

- [ ] **Step 1: Add a failing Event-page browser test**

Load the real Event HTML with the real shared script, select `CabalM TH`,
type `Anniversary` into `#nameEn`, click `#btnSlug`, and assert
`#slug == 'anniversary-mth'`. Replace the slug with `manual-event`, change the
game to `CabalPC SEA`, and assert it is still `manual-event`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -B -m pytest -p no:cacheprovider tests\test_web_calendar_ui.py -q
```

Expected: Event button assertion receives `anniversary`.

- [ ] **Step 3: Switch the Event button to the shared helper**

Replace its `slugify(...)` call with:

```javascript
slugForGame($('nameEn').value || $('nameTh').value, $('game').value)
```

- [ ] **Step 4: Run focused and full verification**

Run:

```powershell
python -B -m pytest -p no:cacheprovider tests\test_web_calendar_ui.py -q
python -B -m pytest -p no:cacheprovider -q
```

Expected: focused tests pass and the full suite reports zero failures.

- [ ] **Step 5: Review without committing**

Run:

```powershell
git diff --check
git status --short
```

Keep the slug work and the earlier calendar fix uncommitted until the user
tests the live pages and approves the milestone.
