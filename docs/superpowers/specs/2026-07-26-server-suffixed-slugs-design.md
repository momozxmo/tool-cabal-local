# Server-suffixed slugs

## Goal

Every slug that the web UI generates automatically must end with the code of
the currently selected game server:

| Game | Suffix |
| --- | --- |
| CabalM TH | `mth` |
| CabalM SEA | `msea` |
| CabalPC TH | `pcth` |
| CabalPC SEA | `pcsea` |

This applies to both the Item Code and Event pages.

## Behavior

- The shared frontend code exposes one helper that slugifies a name and appends
  the selected game's suffix.
- Automatic slug paths use the same helper:
  - the **สร้างให้** button;
  - Item Code drafts filled from an import or handoff when the incoming slug
    still lacks the selected server suffix;
  - Event drafts when the web UI generates their slug.
- An already suffixed slug is left unchanged, so importing
  `summer-event-msea` cannot produce `summer-event-msea-msea`.
- A slug typed directly into the editable slug field is left untouched.
- If the source name contains no usable ASCII characters, automatic generation
  remains empty and the existing warning asks the operator to type a slug.
- If no recognized game is selected, the helper returns the ordinary slug
  without inventing a suffix.

## Structure

`web/static/console.js` owns the game-to-suffix mapping and the shared helper.
`web/static/itemcodes.html` and `web/static/events.html` call it only at their
existing automatic-generation boundaries. Server-side validation remains
unchanged because the generated value still contains only lowercase ASCII
letters, digits, and hyphens.

## Verification

Browser-level tests exercise the real shared JavaScript and assert:

1. all four game names produce the expected suffix;
2. an existing suffix is not duplicated;
3. the Item Code and Event **สร้างให้** flows use the selected game;
4. directly edited slug values are not rewritten merely by changing the game.

The complete Python test suite must remain green. No live Item Code or Event is
saved during verification.
