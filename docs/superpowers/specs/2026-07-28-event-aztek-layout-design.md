# Event Aztek Layout Design

Date: 2026-07-28

## Goal

Make the local Event editor place its existing fields in the same major
sections and columns as Aztek v2, without adding Aztek fields that the team's
workflow does not use.

## Scope

- Reorganize only the Event editor inside `web/static/events.html`.
- Keep the queue, import, preview/create actions, results, and log unchanged.
- Do not add the Aztek Details editor or Status switches.
- Do not change the Event runner's save behavior or create real Aztek records
  during development and verification.

## Desktop Layout

The editor uses an Aztek-like two-column grid.

Left column:

1. General information: slug, Thai Event name, and English Event name.
2. Rewards: add/remove controls and all existing reward-set fields.
3. Claim rules: locked `WINNER`, per-player limit, total quantity, and
   remaining quantity.

Right column:

1. Activity window: activity start and end.
2. Claim window: claim start and end, plus the existing option that mirrors the
   activity window.

The existing warning summary stays above both columns. At the current responsive
breakpoint, the columns collapse to one column without horizontal scrolling.

## Reward Naming

When an imported Event contains exactly one reward set, both reward-name fields
use the Event name. When it contains multiple reward sets, each set keeps the
reward/table name read from the document. A manually added blank Event remains
editable and is not forced to copy a name until data is imported.

## Date Display

All four Event date fields display `YYYY-MM-DD HH:MM:SS`. The stored value may
arrive with either `T` or a space, but copying the activity window into the
claim window must pass through the shared display formatter so `T` never
reappears in the visible claim fields.

## Verification

- Pure Event-plan regression test for single-set and multi-set reward naming.
- Browser regression test for imported Event dates and for toggling/mirroring
  the claim window after values arrive with `T`.
- Browser layout assertions for the left and right sections at desktop width
  and the single-column responsive state.
- Run the complete test suite, including Playwright tests, without clicking the
  real Aztek `สร้าง Event` button.
