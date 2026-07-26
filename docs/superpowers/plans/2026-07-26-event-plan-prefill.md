# Event Plan Prefill Implementation Plan

> **For Codex:** Execute this plan inline with `superpowers:executing-plans`.
> Preserve the existing uncommitted calendar-close and server-suffixed-slug
> changes while editing the same frontend files.

**Goal:** Let the Event page import varied Event workbooks directly or receive
the selected Event sheets from Item Finder, create one editable Event per
worksheet with one reward set per reward group, and match created Bundle IDs
back by stable worksheet/group identity.

**Architecture:** Keep `event_tool.py` as the single workbook parser. Add a
small pure normalizer in `web/event_plan.py`, stamp selected worksheet
provenance before workspace rows are flattened, expose owner-checked draft
endpoints from FastAPI, and carry drafts plus `group_key` through the existing
browser handoff from Item Finder to Bundle to Event. Draft construction remains
read-only; the existing `/api/events/run` route is the only creation path.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, openpyxl, vanilla HTML/CSS/JS,
pytest, Playwright.

---

## Task 1: Pin normalized Event draft behavior

**Files:**

- Create: `web/event_plan.py`
- Create: `tests/test_web_event_plan.py`
- Reference: `event_tool.py`
- Reference: `config.py`

### Step 1: Write failing unit tests

Create compact parser-shaped inputs rather than full workbook fixtures for the
pure normalizer. Pin:

- one worksheet becomes one Event;
- two reward groups in that worksheet become two reward sets;
- `sheet_key` is stable and distinct between worksheets with the same visible
  reward name;
- each reward has a distinct `group_key` based on the sheet plus group;
- start is the supplied `now` date at `00:00:00`;
- TH end is `23:59:59`, SEA end is `22:59:59`;
- claim dates initially equal Event dates and `same_window` is true;
- missing/unreadable end stays `''` and adds a warning;
- a past end remains visible and adds a warning;
- slug includes the selected server exactly once.

Use a fixed `now`, for example `datetime(2026, 7, 26, 15, 30)`.

### Step 2: Run the focused tests and confirm red

Run:

```powershell
pytest -q tests/test_web_event_plan.py
```

Expected: import/behavior failures because `web.event_plan` does not exist.

### Step 3: Implement the pure normalizer

In `web/event_plan.py`, add helpers with no FastAPI/UI dependency:

```python
def sheet_key(sheet_name: str) -> str: ...
def group_key(sheet_name: str, group_name: str, ordinal: int) -> str: ...
def build_event_draft(sheet_name, event, game, now=None) -> dict: ...
def build_event_drafts(parsed_sheets, game, now=None) -> list[dict]: ...
def build_workspace_events(group_meta, game, now=None) -> list[dict]: ...
```

Normalize parser values without guessing:

- `name_th` and `name_en` use the parsed Event name;
- `kind='WINNER'`, uses `1`, quantity/remaining `0`;
- reward names come from the parsed reward/group label;
- missing names/dates remain blank with warnings;
- end dates pass through `config.region_end_of_day`;
- keys are deterministic hashes/slugs of worksheet identity plus ordinal, not
  the visible reward name alone.

Support both direct parser output from `parse_event_plan()` and the
`group_meta` dictionaries from Item Finder.

### Step 4: Run focused tests and confirm green

Run:

```powershell
pytest -q tests/test_web_event_plan.py
```

Expected: all tests pass.

---

## Task 2: Preserve worksheet provenance through Item Finder

**Files:**

- Modify: `web/item_service.py`
- Modify: `web/workspaces.py`
- Modify: `tests/test_web_item_service.py`
- Modify: `tests/test_web_api.py`

### Step 1: Write failing provenance tests

Add tests that import two selected worksheets containing the same reward label.
Assert after `apply_pending`:

- every selected row carries its worksheet identity before merging;
- `group_meta` contains a stable `sheet`, `sheet_key`, and `group_key`;
- repeated visible group names from different sheets do not overwrite each
  other;
- unselected worksheets create no metadata or draft.

Cover both `WorkspaceStore.apply_pending` and the SQL
`WorkspaceRepository.apply_pending` path.

### Step 2: Run focused tests and confirm red

Run:

```powershell
pytest -q tests/test_web_item_service.py tests/test_web_api.py -k "pending or provenance or same_reward"
```

Expected: the second sheet currently overwrites the first by visible group key.

### Step 3: Stamp rows before flattening

Add a shared helper in `web/item_service.py`:

```python
def stamp_sheet_rows(sheet_name, rows):
    ...
```

For each source row:

- copy the row and its `group_meta`;
- retain readable `sources`;
- attach `sheet` and `sheet_key`;
- derive `group_key` from `sheet_key` and the row's group/order;
- use `group_key` as the internal metadata key while preserving `group` as the
  display label.

Call this helper in both pending implementations before `merge_imported`.
Update `merge_imported`, `regroup_results`, `_bundle_name`, and
`build_bundles` only as needed so existing display labels and result ordering
remain unchanged while `group_key` survives.

### Step 4: Run focused tests and confirm green

Run:

```powershell
pytest -q tests/test_web_item_service.py tests/test_web_api.py
```

Expected: all pass, including pre-existing merge/order tests.

---

## Task 3: Add owned Event draft and direct-import APIs

**Files:**

- Modify: `web/app.py`
- Modify: `tests/test_web_activity.py`
- Create or modify: `tests/test_web_event_plan.py`
- Reference: `web/item_service.py`
- Reference: `event_tool.py`

### Step 1: Write failing API tests

Pin:

- anonymous access to `POST /api/events/import` and
  `GET /api/workspaces/{id}/events` returns 401;
- another user's workspace returns 404;
- a selected Event workspace returns only its selected sheet drafts;
- direct import calls the desktop Event parser under the parse lock;
- the upload is removed in `finally` on success and parser failure;
- direct import returns per-sheet counts, drafts stamped with their sheet, and
  skipped/unsupported sheets;
- no Event is saved and `/api/events/run` is not invoked.

Use monkeypatched parser output for API isolation and compact generated `.xlsx`
fixtures for one end-to-end parser test.

### Step 2: Run focused tests and confirm red

Run:

```powershell
pytest -q tests/test_web_event_plan.py tests/test_web_activity.py -k "event and (import or workspace or draft)"
```

Expected: routes return 404.

### Step 3: Add routes

Implement:

```python
@router.get('/api/workspaces/{workspace_id}/events')
def workspace_events(...): ...

@router.post('/api/events/import')
async def events_import(...): ...
```

Requirements:

- retrieve workspaces via `_get_workspace` to retain owner checks;
- require Event mode where applicable;
- direct import uses `_temporary_upload`, `parse_workbook_locked`, and
  `event_tool.parse_event_plan`;
- normalize with `web.event_plan`;
- always unlink uploads;
- audit only filename/game/counts, never workbook contents;
- return partial drafts and warnings instead of inventing required values.

If `parse_event_plan()` does not currently expose skipped sheets, adapt the
desktop parser minimally so its existing callers remain compatible.

### Step 4: Run focused tests and confirm green

Run:

```powershell
pytest -q tests/test_web_event_plan.py tests/test_web_activity.py
```

Expected: all pass.

---

## Task 4: Include Event drafts and stable keys in Bundle preview

**Files:**

- Modify: `web/item_service.py`
- Modify: `web/app.py`
- Modify: `tests/test_web_api.py`
- Modify: `tests/test_web_item_service.py`

### Step 1: Write failing bundle payload tests

For an Event-mode workspace with two sheets and repeated reward labels, assert:

- `/api/workspaces/{id}/bundles` returns `event_drafts`;
- each bundle has its exact `group_key`;
- bundle names remain readable;
- selecting rows does not leak drafts from unselected sheets/groups;
- non-Event modes preserve their current payload shape apart from an optional
  empty `event_drafts`.

### Step 2: Run focused tests and confirm red

Run:

```powershell
pytest -q tests/test_web_api.py tests/test_web_item_service.py -k "bundle"
```

Expected: no `group_key`/`event_drafts`.

### Step 3: Extend existing bundle response

Have `build_bundles` include:

```python
{
    "group_key": internal_key,
    "group": readable_group,
    ...
}
```

Build Event drafts from the same selected keys and add them to the existing
bundle-preview response. Do not create a parallel endpoint or new workflow.

### Step 4: Run focused tests and confirm green

Run:

```powershell
pytest -q tests/test_web_api.py tests/test_web_item_service.py
```

Expected: all pass.

---

## Task 5: Add direct Event import UI

**Files:**

- Modify: `web/static/events.html`
- Modify: `web/static/console.css`
- Modify: `tests/test_web_calendar_ui.py`
- Modify: `tests/test_web_ui.py`

### Step 1: Write failing real-browser tests

Using the existing `_tool_page` helper, pin:

- Event page has an Import button, file input, and sheet-selection dialog;
- mocked `/api/events/import` response lists candidate sheets;
- only checked sheets enter the queue;
- one sheet creates one Event with all of its reward sets;
- imported slug is normalized to selected server exactly once;
- warnings are visible;
- missing end remains blank and disables/blocks preview at the existing API
  validation boundary;
- calendar Done still closes after the markup changes.

### Step 2: Run UI tests and confirm red

Run:

```powershell
pytest -q tests/test_web_calendar_ui.py tests/test_web_ui.py -k "event or calendar"
```

Expected: import controls/functions are missing.

### Step 3: Implement import controls and queue mapping

Mirror the proven Item Code import interaction in `events.html`:

- file chooser and `POST /api/events/import`;
- modal list of sheet candidates;
- select/confirm controls;
- `addDrafts(drafts, from, game)` mapping all editable Event/reward fields;
- display per-draft warnings without hiding editable fields;
- do not add anything to the queue until sheet selection is confirmed;
- preserve current calendar and slug fixes.

### Step 4: Run UI tests and confirm green

Run:

```powershell
pytest -q tests/test_web_calendar_ui.py tests/test_web_ui.py
```

Expected: all pass.

---

## Task 6: Carry drafts through Item Finder → Bundle → Event

**Files:**

- Modify: `web/static/index.html`
- Modify: `web/static/bundles.html`
- Modify: `web/static/events.html`
- Modify: `web/static/console.js`
- Modify: `tests/test_web_calendar_ui.py`
- Modify: `tests/test_web_ui.py`

### Step 1: Write failing handoff tests

Pin in a real browser or DOM-level source tests:

- Event mode shows **ส่งไป Event** and requests
  `/api/workspaces/{id}/events`;
- Item Finder stores selected drafts plus game in session storage;
- Bundle handoff preserves `event_drafts`;
- created Bundle result rows preserve `group_key`;
- Event handoff merges Bundle IDs by exact `group_key`;
- two worksheets with the same visible reward name receive their own IDs;
- unmatched Bundle rows produce a visible warning and are not attached to the
  first Event;
- legacy Item Code handoff continues working.

### Step 2: Run UI tests and confirm red

Run:

```powershell
pytest -q tests/test_web_calendar_ui.py tests/test_web_ui.py -k "handoff or event"
```

Expected: existing Event handoff collapses all Bundle rows into one blank Event.

### Step 3: Extend the current handoff payloads

In `index.html`:

- add `sendToEventPage()` beside the Item Code action;
- fetch the owned Event drafts endpoint;
- pass `event_drafts` when sending Event-mode work to Bundle.

In `bundles.html`:

- retain `event_drafts` in local page state;
- preserve each bundle's `group_key`;
- include `{game, event_drafts, rows}` when sending created Bundle IDs to Event.

In `events.html`:

- replace the one-blank-Event `drainHandoff()` behavior;
- merge normalized Event drafts into the editable queue;
- fill reward `bundle_id` only on exact matching `group_key`;
- log unmatched keys as warnings.

Keep storage one-time (`removeItem` after read) and browser-local.

### Step 4: Run UI tests and confirm green

Run:

```powershell
pytest -q tests/test_web_calendar_ui.py tests/test_web_ui.py
```

Expected: all pass.

---

## Task 7: Remove Item Code date guessing

**Files:**

- Modify: `web/itemcode_plan.py`
- Modify: `tests/test_web_itemcode_plan.py`
- Modify: `tests/test_web_event_plan.py`

### Step 1: Change existing tests to the approved rule

Replace old assertions that missing/unreadable expiry becomes `today + 30` with:

- `start_time` equals current local date at midnight;
- `end_time == ''`;
- notes explain missing/unreadable end and require manual correction;
- valid TH/SEA dates retain their server-specific EOD;
- past dates remain present with a warning.

### Step 2: Run focused tests and confirm red

Run:

```powershell
pytest -q tests/test_web_itemcode_plan.py tests/test_web_event_plan.py
```

Expected: old +30 fallback fails the new assertions.

### Step 3: Update `_window`

Return `(_stamp(start), '')` when parsing returns `None`; do not call
`region_end_of_day` on a missing value. Keep warnings precise for blank versus
unreadable source values.

Remove the unused `timedelta` import if no longer needed.

### Step 4: Run focused tests and confirm green

Run:

```powershell
pytest -q tests/test_web_itemcode_plan.py tests/test_web_event_plan.py
```

Expected: all pass.

---

## Task 8: Full regression and live UI verification

**Files:**

- Verify only; edit failing files if a regression is found.

### Step 1: Run parser/desktop regressions

Run:

```powershell
pytest -q tests/test_event_tool*.py tests/test_itemcode_tool*.py
```

Expected: desktop parser/tool behavior still passes.

### Step 2: Run all web tests

Run:

```powershell
pytest -q tests/test_web*.py
```

Expected: all pass.

### Step 3: Run the full suite

Run:

```powershell
pytest -q
```

Expected: no failures.

### Step 4: Restart the local server safely

Stop only the known process listening on port 8000 after resolving its exact
PID. Start the app without `--reload`, because Playwright sessions must not be
killed by the reloader.

### Step 5: Verify the real UI with a safe import

Using the real browser UI:

1. open `/events`;
2. import the supplied July 2026 PCTH workbook;
3. confirm candidate sheets appear across the varied layouts;
4. select a small sample including a multi-reward Event;
5. verify one Event per sheet, reward grouping, midnight start, PCTH
   `23:59:59` end, warnings, and `-pcth` slug;
6. close the calendar with Done;
7. exercise preview only (`do_save=false`) if an Aztek session is available;
8. do not click any real Create action.

### Step 6: Review the diff and secrets boundary

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Confirm no `.env`, DB, profile, keys, `dist/`, uploaded workbook, screenshot, or
temporary files are staged or added. Do not commit unless the user asks after
reviewing the verified implementation.
