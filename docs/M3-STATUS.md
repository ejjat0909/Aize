# M3 · Look right — status

**0.14.0-m3** (versionCode 16). This is the first slice of M3: the interface stops being stock Material 3 and
becomes Aize's own, and the manoeuvre is drawn as a picture as well as written in words.

M3 is not finished. The rest of it — the full HUD, the app shell and onboarding, the puck blending, the
accessibility pass, the design catalogue — is still open, and `docs/03-roadmap.md` says so per task.

## What shipped

### P1-02 · Icon set

`app/src/main/kotlin/app/aize/ui/icon/`:

- `AizeIconData.kt` — **61 glyphs** as a plain data table (`Map<String, List<String>>` of SVG path data), so the
  set is testable without Compose, a device or a screenshot. House style: 24 × 24 viewport, 1.9 u stroke, round
  caps and joins, no fill (tint comes from `Icon`).
  - 12 manoeuvres: `nav_straight`, `nav_left`, `nav_right`, `nav_slight_left`, `nav_slight_right`,
    `nav_sharp_left`, `nav_sharp_right`, `nav_uturn`, `nav_roundabout`, `nav_merge`, `nav_exit`, `nav_arrive`.
  - 22 place kinds: fuel, food, cafe, parking, atm, pharmacy, police, camera, hazard, accident, jam, closure,
    hospital, mall, hotel, ev, prayer, toilets.
  - The rest interface: close, search, back, star, share, settings, mic, speaker, speaker-off, recenter,
    compass, plus, minus, check, chevron, layers, route, clock, stop, delete, home, work, more, server, theme,
    steps, destination, arrow-up, refresh, play, my-location.
- `AizeIcons.kt` — the same table as `ImageVector`s, built once and cached, plus named `val`s so a typo is a
  compile error rather than an empty box at runtime. An unknown name throws with the list of known names.
- `AizeIconData.byKind` maps an OSM tag or a category id to a glyph. `forKind` reads the **tag value**
  (`amenity=fuel` → `fuel`), because that is what the search service sends.

### P1-03 · Component library

`app/src/main/kotlin/app/aize/ui/component/`:

| Component | What it is |
|---|---|
| `AizeButton` | Small / Normal / Large at the token radii 18 / 24 / 32, heights 36 / 48 / 64. Primary, Tonal, Ghost. Optional leading icon. |
| `AizeIconButton` | 48 dp round target for things that sit over the map. Click and accessibility name land on the same semantics node. |
| `AizeChoiceChip` | Pill filter; selected state is fill *and* weight, so it survives colour blindness and sunlight. |
| `AizeCard` | One radius (XL) and one shadow for the place card, a route row, a saved place. |
| `AizeListRow` | Leading glyph, headline, supporting line, trailing text; 56 dp minimum, one accessibility node. |
| `AizeTextField` | Rounded container, leading glyph, clear button, caret — not Material's outlined field with its label animation. |
| `AizeSheet` | Handle, title, subtitle, close; the search screen and the turn list are both this. |
| `AizeDivider` | One divider colour. |

Wired in: the search sheet, the turn list, the place card, the route chooser and the bottom bar. The bottom bar's
five loose `TextButton`s became named icon buttons, and the server dialog is the one remaining stock
`AlertDialog` + `OutlinedTextField`.

### P1-04 · HUD (partial)

The instruction banner now leads with the manoeuvre glyph in its own 56 dp square, then the distance, the
instruction, a `then` line that carries its own small glyph, and the ETA line. `ManeuverIcons` maps Valhalla's
numeric manoeuvre types to the twelve glyphs; the type is the authority and the words are only a fallback for a
type this build has not seen.

Still missing, and deliberately not faked: the lane strip (the routing tiles carry no `turn:lanes`), the
speed-limit bubble (no `maxspeed`), the report button, and the arrival card.

## Two bugs this slice found

1. **Seven of twelve category chips drew the fallback flag.** The server sends `food`; the icon table had
   `restaurant`. Nothing failed, because a flag is a valid icon. `IconCoverageTest` now asserts that every
   category id resolves to its own glyph, and that the table and the category list cannot drift apart.
2. **Icon buttons had no accessible name.** `Surface(onClick)` does not merge its children, so a screen reader
   got a clickable node with no name and a named node with no action. `AizeIconButton` is now a Box with its own
   background, and the click and the `contentDescription` are on one node — verified with `uiautomator dump`.

A third, smaller one: the first `poi_food` glyph was a fork and knife whose three tines sat two pixels apart at
20 dp and read as a flag. It is a bowl with steam now, and the reason is written next to the path.

## Verification

| Check | Result |
|---|---|
| JVM unit tests | **109**, 0 failures (was 92) |
| `IconCatalogTest` | 6 — every path parses, every glyph stays inside 0.5–23.5 u of the 24 dp box, names follow `nav_`/`poi_`/`ui_`, every kind target exists, `forKind` reads the tag value |
| `IconCoverageTest` | 2 — every category id has its own glyph |
| `AizeButtonTest` | 3 — radii and heights come from the tokens, and a corner is never more than half the height |
| `ManeuverIconTest` | 6 — the four turn kinds stay distinct, U-turns are not turns, arrival and roundabout are their own glyphs, an unknown type falls back to the words, a street name cannot choose the turn |
| On device (emulator, API 34) | banner glyph matches the instruction; turn list glyphs match all nine instructions in the 9.1 km demo route; search sheet chips and rows render with their icons |

Screenshots: `docs/verification/m3-banner.jpg`, `m3-turnlist.jpg`, `m3-search.jpg`.

## Next in M3

P1-08 app shell and onboarding, P1-10 accessibility pass, P1-07 design catalogue with screenshot tests, P2-05
puck blending (the pipeline already measures 16.8 dB nearest bucket against 30.6 dB for the two-bucket blend),
then the rest of P1-04 once the tiles carry the lane and speed data.
