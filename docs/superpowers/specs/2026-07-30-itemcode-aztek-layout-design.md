# Item Code Aztek Layout Design

Date: 2026-07-30

## Goal

Make the Local Item Code editor follow the major layout and reward navigation
of the current Aztek v2 create page while preserving the Local queue, import,
preview, and create workflow.

## Scope

- Reorganize only the Item Code editor in `web/static/itemcodes.html`.
- Keep the queue/import controls above the editor.
- Keep preview, real-create actions, results, and logs below the editor.
- Preserve all existing field IDs, draft data, queue storage, and API payloads.
- Do not add Item Code descriptions, status switches, quantity controls, or
  reward conditions from Aztek.
- Do not create real Aztek records during implementation or verification.

## Desktop Layout

The editor uses an Aztek-like two-column grid.

Left column:

1. General information panel: Thai name, English name, and slug.
2. Settings panel: locked `ALL` type, total uses per user, start time, and end
   time.

Right column:

1. Rewards panel header with the existing add-reward button.
2. Reward-set tabs.
3. The form for only the active reward set.

The two columns use equal available width, matching the current Aztek form.
The Local visual theme and existing page header remain unchanged.

## Reward Tabs

- Each reward set has one pill-shaped tab with the exact pattern
  `N ชุดที่ N`, for example `1 ชุดที่ 1` and `2 ชุดที่ 2`.
- Only the active reward card is rendered below the tabs.
- Adding a reward set appends it and immediately selects its tab.
- Removing the active reward selects the next available set; if there is no
  next set, it selects the previous set.
- At least one reward set must remain.
- Switching tabs changes presentation only. It must not discard edits or alter
  reward ordering.
- A long tab row wraps inside the reward panel instead of causing horizontal
  page scrolling.

## Responsive Layout

At `1100px` viewport width and below, the two columns collapse to one column:
general information, settings, then rewards. Reward tabs remain usable and
wrap as needed.

## Accessibility

- The tab strip uses tab semantics with an accessible label.
- Each tab exposes selected state.
- The active reward panel is associated with its tab.
- Tabs remain keyboard-focusable.
- Existing labels and form control IDs remain unchanged.

## Data and Automation Compatibility

- The queue continues to store every reward set, including inactive sets.
- `renderSets()` renders only the active reward card, but `jobFrom(entry)`
  must still serialize every reward in its original order.
- Import and handoff continue to create all reward sets before selecting the
  first set.
- Existing Bundle ID, code limitation, code type, fixed-code list, prefix, and
  generated-code count behavior remain unchanged.
- Preview and create automation remain unchanged.

## Verification

- Browser regression test for the Aztek-like desktop column placement and
  single-column responsive state.
- Browser regression test that multiple rewards produce multiple tabs and only
  the selected reward card is visible.
- Browser regression tests for add, switch, and remove selection behavior.
- Data regression test that inactive reward sets remain in the API payload.
- Run the complete test suite without clicking the real Aztek
  `สร้าง Item Code` button.
- Visually compare the Local editor against the inspected Aztek v2 create page
  at desktop width.
