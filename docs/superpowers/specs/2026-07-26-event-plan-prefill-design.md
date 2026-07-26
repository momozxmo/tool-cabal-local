# Event plan import and prefill

## Goal

Build the Event page's missing plan workflow without inventing a second Excel
parser:

1. import a plan directly on the Event page or use the sheets selected in Item
   Finder;
2. create one editable Event draft per selected worksheet/activity;
3. create one reward set per reward group in that Event;
4. carry created Bundle IDs back to the correct reward sets;
5. preview safely before any real Event is created.

The July 2026 PCTH workbook is the main real-world reference. It contains 55
worksheets with several layouts; the desktop `event_tool.parse_event_plan()`
currently recognizes 48 Event candidates.

## Source of truth

The web reuses the desktop parsing rules in `event_tool.py`:

- `parse_event_plan()` produces worksheet-level Event data for direct Event
  import.
- `parse_event_plan_workbook()` produces Item Finder rows from the same file.
- `_parse_any_sheet()`, `_plan_event_name()`, `_plan_period()`, and the
  `Web Reward` detector remain the layout adapters.

New layouts are added as desktop parser adapters. The web must not grow a
separate fuzzy scanner with different behavior.

Non-Event worksheets such as schedules, notes, item databases, and appendices
do not become Event drafts merely because they contain a date or an ItemKind
column.

## Normalized draft

`web/event_plan.py` converts parser output into editable dictionaries with this
shape:

```text
EventDraft
  sheet_key       stable key for the imported worksheet
  sheet           worksheet display name
  name_th
  name_en
  slug
  kind            WINNER
  uses_per_user   1
  quantity        0
  remaining       0
  start_event
  end_event
  start_claim
  end_claim
  same_window     true
  rewards[]       RewardDraft
  warnings[]

RewardDraft
  group_key       stable worksheet + reward identity
  group           reward display name
  name_th
  name_en
  uses_per_user   1
  limited         false
  quantity        empty
  remaining       empty
  bundle_id       empty until handoff
```

Every field shown on the Event page remains editable. `sheet_key` and
`group_key` are matching metadata, not Aztek form fields.

## Worksheet and group identity

One selected worksheet/activity produces one Event. All reward tables detected
inside that worksheet become reward sets of that Event.

Reward names can repeat in different worksheets, so a visible reward name alone
is not an identity. The import path attaches worksheet provenance before rows
are flattened into a workspace. Bundle definitions and handoff rows preserve
the resulting `group_key`. This prevents a reward named `Lucky Draw` in one
Event from receiving the Bundle ID created for another Event.

Existing Item Finder and Bundle labels stay readable. Internal keys are carried
as metadata instead of being shown as long composite names.

## Date rules

The Event and Item Code draft builders use the same rules:

- Start is always the current application-local date at `00:00:00`.
- The document supplies the end date.
- CabalM TH and CabalPC TH end at `23:59:59`.
- CabalM SEA and CabalPC SEA end at `22:59:59`.
- Event claim start/end initially mirror Event start/end.
- The operator can untick the same-window control and edit claim dates.
- A missing or unreadable document end date stays blank and adds a warning.
  The API's existing required-date validation blocks preview and creation until
  the operator fills it.
- A past end date remains visible with a warning; the ordering validation blocks
  it until corrected.

The old Item Code `today + 30 days` fallback is removed. Tests pin the shared
midnight/EOD behavior for both tools.

## Import flows

### Direct import on the Event page

The Event page gets an **Import file plan** button and sheet-selection dialog,
matching the Item Code page. `POST /api/events/import`:

1. accepts a temporary `.xlsx` upload and selected game;
2. runs `event_tool.parse_event_plan()` through the existing workbook parse
   lock;
3. returns candidate sheets and normalized drafts;
4. deletes the temporary file;
5. stores no workbook contents or Aztek state.

Nothing enters the queue until the operator confirms the selected sheets.

### Selected sheets from Item Finder

Applying a pending Event import stamps each selected row's metadata with its
worksheet provenance before merging it into the workspace. A new owned endpoint,
`GET /api/workspaces/{workspace_id}/events`, returns drafts for only those
selected sheets.

The Item Finder page offers **Send to Event** alongside the existing Item Code
handoff. It passes drafts through session storage and never exposes another
user's workspace.

## Bundle handoff

When an Event-mode Item Finder workspace moves to the Bundle page, its Event
drafts travel with the existing one-time handoff payload. The Bundle page keeps
them only in browser state. After Bundles are actually created and have IDs,
the Event handoff contains:

- the selected game;
- normalized Event drafts;
- created Bundle ID rows carrying `group_key`.

The Event page merges drafts into its local editable queue and fills each reward
set by exact `group_key`. A row without a matching draft is shown as a warning
and is not silently attached to the first Event.

Direct-import drafts already saved in the Event page's local queue use the same
matching path when the operator returns from creating Bundles.

## Unknown or partial layouts

Parser adapters may return a partial Event when they can identify a worksheet
and reward tables but cannot read every required field. The Event page shows the
read fields, leaves missing required fields blank, and lists warnings by sheet.
It never guesses a date, Event name, reward group, or Bundle relationship.

A worksheet with no recognized Event structure and no reward tables is skipped
and reported as unsupported rather than turned into an empty Event.

## Safety and validation

- Import, draft building, and tests never press an Aztek save button.
- Preview remains `do_save=false`.
- Real creation retains the existing confirmation and owner/audit checks.
- No password, Aztek cookie, pairing token, or raw storage state enters import
  payloads or logs.
- Uploaded workbooks remain temporary and are removed in `finally`.
- Existing desktop tkinter behavior remains supported because parser changes
  are shared, not replaced.

## Verification

Tests use compact generated workbooks modeled on the real layouts:

- `Event Name` + `Reward:` + `ItemKind`;
- `Web Reward` / Monthly Top Spender;
- shifted Start/End columns;
- repeated reward names across two worksheets;
- unsupported schedule/note sheet;
- missing and past end dates.

Coverage includes direct Event import, selected-sheet ownership, workspace
drafts, one-sheet-to-one-Event grouping, Bundle ID matching by `group_key`,
editable frontend queues, Event and Item Code midnight/EOD rules, and preview
save safety. The full desktop/web test suite must pass.
