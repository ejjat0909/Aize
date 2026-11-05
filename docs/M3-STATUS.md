# M3 · Look right — status

**0.16.0-m3** (versionCode 18). Three slices of M3 so far: the interface stops being stock Material 3 and
becomes Aize's own (icons, components, the manoeuvre drawn as well as written), the app gains a first run that
explains itself before it asks for anything, and what it says is now what a screen reader reads.

M3 is still not finished: the design catalogue with screenshot tests and the P2-05 sprite change are open, and
`docs/03-roadmap.md` says so per task.

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

### P1-08 · App shell and onboarding

`app/src/main/kotlin/app/aize/ui/`:

- `AppShell.kt` — `AizeApp()` is what `MainActivity` now sets. Two states, not a navigation graph: the map is
  where the app lives, and the tour is the only other place. The flag is read once per composition, so finishing
  the tour shows the map immediately instead of after a restart.
- `onboard/Onboarding.kt` — the flow as a **pure step machine**: `steps`, `next()`, `back()`, `position()`,
  `progress()`, `isLast()`, and the persisted `onboarding_done_v1` flag. No Compose in it, so the order of the
  steps is unit-tested rather than eyeballed.
- `onboard/OnboardingScreen.kt` — five steps: **Welcome → How it works → Location → Privacy → Ready**. Progress
  dots that stretch rather than add a number, one primary action, Back, and a skip that disappears on the last
  step (where "Start driving" is the same door).
  - The location permission is requested **on the step that explains it**, not as a surprise over the map. A
    refusal is answered with "Ask again" and a sentence that says what still works — a named fallback, not a
    dead end, because a refused permission is not an error.
  - The telemetry switch defaults **off** and writes straight through to `Telemetry.setEnabled`, which is the
    same switch that governs the sink.
  - The server address is shown on the last step **only in debug builds**: which host a build talks to is a
    developer fact, not a user-facing one.
- `component/AizeSwitch.kt` — the labelled switch P1-03 was missing: the whole row is a `Role.Switch` toggle,
  the track and knob follow the motion tokens, and the knob is coloured per state so it is visible against both
  a dark off-track and a light on-track.
- The server dialog gains **"Show the tour again"**, so `Onboarding.reset()` is reachable and the tour is not a
  one-time event for someone who skipped it.

### P1-10 · Accessibility pass

The app was readable and unusable by voice: half the controls had no name, no control announced its state, and
three colours sat under the contrast floor the platform asks for. Fixed as data and tests rather than a sweep of
opinion.

`app/src/main/kotlin/app/aize/ui/a11y/`:

- `Contrast.kt` — WCAG maths over plain ARGB ints, so it is a JVM test and not a colour picker: `luminance()`,
  `ratio()`, `blend()` (what a semi-transparent colour finally looks like on its background), `ratioOn()`. The
  floors are named constants — `BODY_TEXT` 4.5, `LARGE_TEXT` 3.0, `NON_TEXT` 3.0.
- `AizeAlpha` — the two alphas the banner actually uses. `BANNER_SECONDARY`/`BANNER_TERTIARY` are **0.92, not
  0.8**: `onPrimary` at 0.8 on the light primary measures **4.00:1**, under the 4.5 body floor. At 0.92 it clears.
- `Spoken.kt` — the sentences a screen reader should hear, built by pure functions so they can be asserted:
  `banner(distance, instruction, then, eta)`, `route(index, count, distance, minutes, via, badges, selected)`,
  `place(name, kind, distance, saved)`. A banner reads *"52 m. Bear left onto Jalan Stesen Sentral. then Make a
  left U-turn onto Jalan Tun Sambanthan."* — distance first, because that is the thing that is changing.

Semantics changed:

- **The banner is one node** with that sentence as its `contentDescription`, instead of five unrelated Texts.
  It is deliberately **not** a live region: the distance counts down every second, and a live region would make
  the phone talk over itself while the announcer is already speaking the turn.
- **Category chips are `Role.Checkbox` and `selectable`** — a chip that is on now says it is on. Before, the
  selection was invisible to TalkBack.
- **A route row reads as a sentence**: *"Route 2 of 3. 9.1 km, 21 minutes, via Jalan Ampang, fastest, shown on
  the map."* Which route it is comes first, because "2 of 3" is what the user is choosing between. "On map" is
  filtered out of the badges — the string already ends with "shown on the map", and saying it twice is noise.
- **A place card header merges** into *"Car Park D2. Parking."* with `heading()`, while the action buttons stay
  their own nodes, so a swipe still reaches Directions directly.
- **Sheet titles and the "N routes" header are headings**, so TalkBack can jump between them.
- **`AizeCard`/`AizeListRow` merge their children when clickable** — `Surface(onClick)` does not, which is the
  same trap that hid the icon-button names in the previous slice.

Large fonts, measured rather than eyeballed: at **1.5x** and **2.0x** the banner wraps to two lines per
instruction and stays inside its card; the "then" line was `maxLines = 1` and truncated the street name it
exists to say, so it is 2. The bottom bar's *"KL Sentral → KLCC (recorded) · 9.1 km"* was one string, which at
1.5x wrapped and left the separator dangling at the end of a line — the label and the distance are now two
Texts, the label ellipsises and the distance stays whole.

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
| JVM unit tests | **129**, 0 failures (was 114) |
| `ContrastTest` | 5 — the core palette clears 4.5:1 in both themes, the banner's two secondary lines clear it *at the alpha the code uses*, meaning-carrying graphics clear 3:1, the route colours are readable against the map land, and `blend()` is the arithmetic the eye does |
| `SpokenTest` | 6 — the banner reads distance first and never doubles a full stop, missing parts do not leave holes, a route says "Route 2 of 3" before its numbers, badges are lowercased into the sentence, "1 minute" is not "1 minutes", and a place card names the kind only when there is one |
| `TouchTargetTest` | 4 — `AizeSize.TOUCH_TARGET` is 48 dp, Normal and Large meet it in ink as well as in target, Small stays 36 dp inside a sheet, and the banner's 96 dp floor holds |
| `OnboardingTest` | 5 — the flow starts at Welcome and ends at Ready, walking forward visits every step in order, `back` undoes `next`, progress is monotonic and ends at 1, and the location step comes after the step that explains it |
| `IconCatalogTest` | 6 — every path parses, every glyph stays inside 0.5–23.5 u of the 24 dp box, names follow `nav_`/`poi_`/`ui_`, every kind target exists, `forKind` reads the tag value |
| `IconCoverageTest` | 2 — every category id has its own glyph |
| `AizeButtonTest` | 3 — radii and heights come from the tokens, and a corner is never more than half the height |
| `ManeuverIconTest` | 6 — the four turn kinds stay distinct, U-turns are not turns, arrival and roundabout are their own glyphs, an unknown type falls back to the words, a street name cannot choose the turn |
| On device, screen reader | `uiautomator dump` (what TalkBack reads): the banner is one node, *"52 m. Bear left onto Jalan Stesen Sentral. then …"*; the selected chip reports `checkable=true checked=true`; a place card is *"Car Park D2. Parking."*; a route row is *"Route 1 of 2. 367 km, 248 minutes, via E2, fastest, shortest, tolls, motorway, shown on the map."* — saved in `docs/verification/m3-a11y-tree.txt` |
| On device, large fonts | 1.5x and 2.0x: banner instructions wrap to two lines inside the card, the "then" line keeps its street name, the bottom bar keeps the distance whole while the label ellipsises |
| On device (emulator, API 34) | banner glyph matches the instruction; turn list glyphs match all nine instructions in the 9.1 km demo route; search sheet chips and rows render with their icons |
| On device, first run | fresh install opens the tour; **denying** the location dialog leaves the step usable ("Ask again" plus what still works); the consent switch writes `telemetry_opt_in=true` to `aize.xml`; finishing writes `onboarding_done_v1=true` and the map appears; force-stop and relaunch goes **straight to the map** |

Screenshots: `docs/verification/m3-banner.jpg`, `m3-turnlist.jpg`, `m3-search.jpg`, `m3-a11y-chooser.jpg`,
and the first-run flow in `m3-onboarding-{welcome,howitworks,location,privacy,ready}.jpg`. The semantics
themselves are text: `docs/verification/m3-a11y-tree.txt`.

## Next in M3

P1-07 design catalogue with screenshot tests, then P2-05 puck blending (the pipeline already measures 16.8 dB
nearest bucket against 30.6 dB for the two-bucket blend), then the rest of P1-04 once the tiles carry the lane
and speed data.
