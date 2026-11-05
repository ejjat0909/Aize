# 03 · Roadmap to done

> Generated from `docs/backlog.csv` by `scripts/generate_roadmap.py` on 2026-11-05. The backlog is the work breakdown in `docs/02-aize-build-plan.md`; this file adds what is actually built, what is next, and in what order. Re-run the script when a task lands instead of editing this by hand.

## Where the app is today

Version 0.15.0-m3. A debug APK installs and runs on a phone: purple MapLibre basemap from bundled PMTiles, purple puck and destination marker, live Valhalla routing from a server with a permanent address, place search over 685k named places with twelve one-tap categories and the last ten searches remembered, and turn-by-turn guidance that now keeps working with the screen off. It speaks through system TTS (prepare and imminent prompts, muteable), shows distance, time left and an arrival clock, re-routes when you leave the route, and follows the clock into dark mode. A destination can now come back as up to three routes, listed with their distance, time and tolls, so the driver picks the way rather than accepting one, a place card lets you look before you go (Directions, Save, Share) and a turn list shows the whole route. The 3D family — pins, puck and the navigation arrow — is rendered from one soft-touch material profile and a wide-light rig, so nothing on the map is candy-glossy, and a grey route can be tapped on the map as well as in the list. The interface is now drawn from its own component library and a 61-glyph icon set rather than stock Material, and the banner shows the manoeuvre as a picture as well as in words. A first run explains what the app is, how it works, why it wants location and what it does with your data before it asks for anything, and a refused permission is answered rather than ignored. 114 JVM unit tests pass.

What it is not yet: no lane guidance or speed-limit signs (the routing tiles carry neither), no reports or traffic, no settings screen, and the release build is unsigned.

| Phase | Name | Tasks | Planned | Left (est.) | MVP |
|---|---|---|---|---|---|
| P0 | Foundations & decisions | 11 | 33 pd | 4.5 pd | yes |
| P1 | Design system & app shell | 12 | 76 pd | 47 pd | yes |
| P2 | Map & location | 13 | 76 pd | 40 pd | yes |
| P3 | Search, places & routing | 11 | 72 pd | 43 pd | yes |
| P4 | Navigation engine & voice | 14 | 110 pd | 77 pd | yes |
| P5 | Live traffic & community | 12 | 101 pd | 101 pd | yes |
| P6 | Planning, sharing & accounts | 7 | 53 pd | 53 pd | no |
| P7 | Android Auto | 5 | 36 pd | 36 pd | no |
| P8 | Polish, accessibility & performance | 8 | 48 pd | 48 pd | no |
| P9 | Hardening & launch | 7 | 48 pd | 48 pd | no |
| **all** | | **100** | **653 pd** | **497.5 pd** | 337 pd MVP |

`pd` is person-days as planned in the WBS. "Left" counts finished tasks at zero and half-done ones at half, so treat it as an estimate, not a promise. On that basis the MVP has **190.5 pd** left of the 337 pd planned for it, and the whole plan has 497.5 pd left of 653.

## The order to do it in

Milestones are the order that gets a usable product soonest, not the phase numbering. Each one ends with something you can hand to a person.

| Milestone | What you can do at the end | Tasks |
|---|---|---|
| **M1 · Drive with it** | A phone in a car bracket guides a real drive: voice prompts, speed-adaptive turn triggers, lane guidance, ETA that settles, and navigation that survives the screen turning off. | P4-04, P4-05, P4-07, P4-08, P4-11, P4-12, P2-09, P2-11 |
| **M2 · Choose where to go** | Search with categories and recents, a place card with actions, up to three routes with tolls and a turn list, favourites, and all nine map pins in use. | P3-01, P3-04, P3-05, P3-06, P3-08, P3-11, P2-07 |
| **M3 · Look right** | The design spec is realised: the component library, the HUD pieces, motion tokens, a puck that blends instead of popping, and accessibility built in rather than bolted on. | P1-02, P1-03, P1-04, P1-05, P1-07, P1-08, P1-10, P2-05, P2-06 |
| **M4 · Ship a beta** | Signed AAB, measured performance budgets, Play internal testing with real testers, crash-free above 99.5%. | P0-09, P0-11, P8-06, P8-07, P8-08, P9-03, P9-05 |
| **M5 · Community** | Report a hazard in three taps, see alerts on your route, traffic-coloured roads, and probes that feed the traffic model. | P5-03, P5-04, P5-05, P5-06, P5-12, P5-07, P5-08 |
| **M5b · Full traffic** | Real probe ingest and aggregation, moderation, and map matching that fixes the remaining false-reroute cases. | P5-01, P5-02, P5-09, P5-11, P4-01, P4-03 |
| **M6 · Ship it** | Localised, audited, measured over 50 real drives, and published. | P8-01, P8-02, P8-03, P8-04, P8-05, P9-01, P9-02, P9-03, P9-04, P9-05, P9-06, P9-07 |
| **Later · Beyond the MVP** | Accounts, planned drives, ETA sharing, Android Auto, offline regions, original voice packs. | P6-01, P6-02, P6-03, P7-01, P3-10, P6-06, P2-12, P4-09, P4-10 |

## Start here: the next six pieces of work

### 1. Turn-by-turn from real GPS  ·  P4-04, P4-05

Today the banner advances only as far as the next maneuver and the distance is a straight-line projection. Make it a proper guidance engine: speed-adaptive prepare/approach/now triggers, distance to the maneuver point rather than to the segment, remaining time and distance, and an arrival clock that does not jump around.

### 2. Voice  ·  P4-08

Android `TextToSpeech` first, with a scheduler that de-duplicates prompts and respects audio focus and ducking. The 51-prompt catalogue in `docs/02-aize-build-plan.md` §8.2 is the contract; studio recordings come later.

### 3. Navigation that survives the screen  ·  P2-09, P4-12

Move the navigation loop into a foreground service with the `location` type, an ETA notification, and Android 14 compliance. Without it the app stops guiding when the screen turns off, which is the single biggest thing between this and a usable driving app.

### 4. A test harness you can trust  ·  P4-11

GPX/NMEA replay with a speed multiplier and scripted scenarios (missed turn, tunnel, GPS jump, U-turn). Right now every behaviour is checked by hand on an emulator, which does not scale and cannot catch regressions.

### 5. Place card and route choice  ·  P3-04, P3-05, P3-06

Tapping a search result should open a card (distance, ETA, Go/Save/Share), and Go should offer up to three routes with tolls and a turn list before starting.

### 6. Release signing and a real beta  ·  P0-11, P9-03, P9-05

A signed AAB, the Play data-safety form, the foreground-service and background-location declarations, and an internal testing track.

## Phase by phase

### P0 · Foundations & decisions

*Exit criterion:* A walking skeleton: purple map, a puck, a route drawn.

11 tasks, 33 pd planned, 4.5 pd left. 8 done, 3 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P0-01 | Decision workshop: pilot region, minSdk, ABIs, repo licence, brand assets, domain, monetisation stance → ADR files | 2 | yes | done |
| P0-02 | Monorepo scaffold: Gradle (KTS + version catalog), Rust workspaces (core, backend), buf/protobuf module, docs, design | 3 | yes | done |
| P0-03 | Pin toolchains: JDK 21, AGP, Kotlin 2.x + Compose compiler, NDK (≥ r27), Rust stable + android targets, cargo-ndk, buf, Valhalla/Planetiler/Photon container images | 2 | yes | done |
| P0-04 | CI: lint (ktlint/detekt, clippy, rustfmt), unit tests, assemble, cargo-deny (licences), dependency review, caching | 3 | yes | done |
| P0-05 | Design-token pipeline: tokens JSON (exists: design/tokens) → Compose theme + MapLibre palette; contrast audit as CI gate | 3 | yes | done |
| P0-06 | Legal baseline: third-party licence inventory + NOTICE, trademark/name clearance for 'Aize' and logo, privacy-policy skeleton, 'no Waze assets' policy + checker script | 3 | yes | done |
| P0-07 | Data pipeline v0 for the pilot region: OSM extract → Planetiler → PMTiles; Valhalla tile build; Photon import; docker-compose dev stack | 5 | yes | part |
| P0-08 | Walking skeleton: Compose app + MapLibre purple style + location puck + hard-coded Valhalla route drawn | 5 | yes | done |
| P0-09 | Performance harness: Macrobenchmark module, Baseline-Profile generator module, Perfetto capture scripts, JankStats in debug; first numbers committed | 3 | yes | done |
| P0-10 | Crash/telemetry scaffolding (privacy-first, opt-in), remote feature-flag client, build-config for staging/prod | 2 | no | part |
| P0-11 | Security baseline: secrets handling (no keys in repo), signing config, dependency pinning, SAST in CI | 2 | no | part |

- **P0-01** — Decision record in `docs/adr/d-decisions.md` (D1 pilot region, D5 licence GPL-3.0, D7 minSdk 26, D4 no ads). Trademark clearance is the one item still open, and it needs the owner (D6).
- **P0-02** — Gradle KTS + version catalog, `core/` and `backend/` Rust workspaces, `proto/` linted with buf, design pipeline, docs, CI.
- **P0-03** — Gradle 9.8.2, AGP 9.4.1, Kotlin 2.4.21, compileSdk 37, Rust stable 1.99, buf 1.75, JDK 17. No NDK, so the UniFFI bridge (P4-06) waits; no Docker, so Valhalla runs from the prebuilt wheel.
- **P0-04** — Four CI jobs: Android (token drift, no-Waze gate, unit tests, debug + R8 release build), Rust (fmt, clippy `-D warnings`, tests), proto (buf lint/build), security (CodeQL).
- **P0-06** — GPL-3.0 `LICENSE`, updated `NOTICE.md`, `docs/PRIVACY.md` skeleton, and `scripts/check_no_waze_assets.py` as a CI gate.
- **P0-07** — Valhalla 3.9.1 (735 tiles) and the 685k-place FTS5 index are built and running. Own Planetiler tiles are not: `server/dev/docker-compose.yml` is written but has never been run (no Docker here).
- **P0-09** — `:benchmark` Macrobenchmark module, JankStats in debug, Perfetto script, baseline-profile generator. First numbers: 3.54 s cold TTID on the software-rendered emulator — `docs/verification/p0-perf.md`.
- **P0-10** — Opt-in `Telemetry` (no-op unless enabled, logcat sink only, nothing leaves the device) and `FeatureFlags` with defaults on parse failure. No remote fetch and no crash reporter: ADR-19 leaves the vendor open.
- **P0-11** — Release signing from environment variables only, R8 release build proven (47 MB), CodeQL in CI. No dependency verification metadata and no secrets scan yet.

### P1 · Design system & app shell

*Exit criterion:* Every screen is built from the Aize component library; nothing is stock Material.

12 tasks, 76 pd planned, 47 pd left. 1 done, 7 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P1-01 | Compose theme from tokens (light/dark/dynamic-off), typography (Figtree subset + Roboto fallback), shapes, elevation, spacing | 4 | yes | part |
| P1-02 | Icon set v1 (~60): nav arrows, lane arrows, report types, POI categories, UI glyphs — SVG → ImageVector on a 24 dp grid | 8 | yes | part |
| P1-03 | Component library v1: buttons (S/M/L radii 18/24/32), icon buttons, chips/pills, cards, dialogs, bottom sheet (peek/half/full, 150 ms slide), snackbar, text fields, switches, list rows, segmented control, tooltip | 10 | yes | part |
| P1-04 | Navigation HUD components (stateless): instruction banner + lane strip, ETA bar (compact/expanded), speed bubble + limit sign, report FAB, recenter button, compass, alert pill (pop-in), arrival card | 14 | yes | part |
| P1-05 | Motion kit: easing/duration tokens as AnimationSpecs, popIn/sheet/page transitions, reduced-motion replacement, RenderThread-friendly (graphicsLayer) variants | 3 | yes | part |
| P1-06 | Original Lottie/Rive assets: splash, report button idle/press, points/confetti, loaders (skeleton), mic listening/speaking states | 8 | no | — |
| P1-07 | Design-catalogue module + screenshot tests (Paparazzi/Roborazzi) for every component × light/dark × font-scale 1.3 × RTL | 5 | yes | — |
| P1-08 | App shell: single-Activity + type-safe Navigation, Android 12 splash + animated icon, onboarding, permission rationale flows (precise location → background → notifications → mic), consent screen | 8 | yes | part |
| P1-09 | Settings framework: declarative tree DSL (id path, type, search, deep link), DataStore persistence; seed with the v1 subset (Appendix C) | 5 | yes | — |
| P1-10 | Accessibility baseline: TalkBack semantics, large fonts, colour-blind-safe traffic cues (icon/pattern + colour), contrast gate, reduced motion | 5 | yes | part |
| P1-12 | 3D asset pipeline in CI: pinned, checksum-verified Blender 4.5 LTS; `assets3d/build_all.sh`; the verification gates (camera anchor/pitch, clip, brand colour, WebP round-trip, silhouette/raised/image/pop, size budget) as a required check; sprite sheets and manifests published as build artifacts | 3 | yes | done |
| P1-11 | i18n pipeline: Android resources + Weblate/Crowdin, pseudo-locales, RTL enabled (supportsRtl=true), plural/units formatting | 3 | no | — |

- **P1-01** — Light and dark themes generated from tokens. Typography is still default Roboto (no Figtree subset); spacing/shape roles only partly applied.
- **P1-02** — A house icon set in `ui/icon/`: 61 stroked glyphs on a 24 dp grid — twelve manoeuvres, twenty-two place kinds, the rest interface — built from one data table so they are unit-tested (`IconCatalogTest` parses every path, bounds every glyph, and checks every category id resolves). Not yet: the ~60-icon target is met but the set is drawn, not reviewed; no filled/duotone variants and no automated screenshot comparison.
- **P1-03** — `ui/component/`: `AizeButton` (small/normal/large at the token radii 18/24/32, primary/tonal/ghost), `AizeIconButton`, `AizeChoiceChip`, `AizeCard`, `AizeListRow`, `AizeTextField`, `AizeSheet` and `AizeDivider`. The search sheet, turn list, place card, route chooser and bottom bar now use them; the server dialog still uses a stock `AlertDialog` and `OutlinedTextField`. Not yet: segmented control, switch, snackbar, tooltip, dialogs, and the 150 ms sheet transition.
- **P1-04** — The banner now leads with the manoeuvre glyph in its own 56 dp square, then distance, instruction, the `then` line with its own small glyph, and the ETA line. No lane strip (the tiles carry no `turn:lanes`), no speed bubble (no `maxspeed`), no report button, no arrival card.
- **P1-05** — Durations, easings and springs live in `design/tokens/aize-purple.tokens.json` and are emitted as `AizeMotion`, `AizeSprings` and `AizeChoreography` by `design/generate_android.py`, so the `--check` gate keeps them from drifting. In use: the instruction banner slides in and out, a maneuver change cross-fades the text while the distance countdown stays still, chooser rows stagger in, the sheet springs between heights, and the puck eases along the short arc between GPS fixes. `rememberMotionEnabled()` reads Android's animator duration scale and zeroes every duration when animations are switched off, so "remove animations" removes them rather than slowing them down. Not done yet: page forward/back transitions between screens, and the `graphicsLayer` (RenderThread) variants of the transitions.
- **P1-08** — `AizeApp` is the shell: one Activity, and the first run is a five-step tour (welcome, how it works, location, privacy, ready) held in `ui/onboard/Onboarding.kt` as a pure step machine with the done-flag in `SharedPreferences`. The location permission is asked for on the step that explains it, a refusal is answered with a named fallback rather than a dead end, the telemetry toggle defaults off and writes through to `Telemetry`, and the tour can be replayed from the server dialog. Not yet: a real navigation graph (the map is still the only destination) and an in-app privacy policy page.
- **P1-10** — Icon-only buttons carry a merged semantics node with a name and a click action (the round-bar buttons read as "Turn list", "Search", "Theme: Auto, tap to change"), and the consent switch is a `Role.Switch` toggle over the whole row. Not yet: a full TalkBack pass, dynamic type, and contrast audits.

### P2 · Map & location

*Exit criterion:* The map looks and moves like the design spec; the puck is smooth at 60 fps.

13 tasks, 76 pd planned, 40 pd left. 2 done, 8 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P2-01 | `:map` module: MapLibre Native (SurfaceView mode, Vulkan/OpenGL artifact decision), lifecycle, style loading, tile cache config, frame-stats hook | 5 | yes | part |
| P2-02 | Style generator: day/night MapLibre style JSON from tokens — categories analogous to the 49 Waze layers (freeway/primary/secondary/street/alley/private/trail/ramp, rail, ferry, water, parks, buildings, parking, cities, labels + shields) with zoom-interpolated width/colour/label size; golden-image tests | 8 | yes | done |
| P2-03 | Tile pipeline hardening: Planetiler profile (only needed layers), PMTiles on object storage + CDN, attribution (OSM ODbL), weekly refresh job | 5 | yes | part |
| P2-04 | `MapController` API (mirrors observed Waze camera API): centerOnMe/Position, showOverview(route), compass modes, margins/insets for HUD, user-location offset, zoom in/out, speed-adaptive zoom/tilt, animated with silky easings; camera presets (overview 0 deg, browse 30, drive 45, navigate 60) are the pointer sprite's pitch buckets, so every steady state is on-grid | 6 | yes | part |
| P2-05 | Pointer overlay (`PointerOverlay` composable) over the map: arrow / puck / car-skin sprites from `assets3d` - two pitch buckets warped to the true pitch/yaw by one affine matrix (see `assets3d/README.md#runtime-algorithm`), blended by pitch, dissolve on a heading-bucket change; positioned by the map projection; 60 fps dead-reckoned interpolation between GPS fixes; accuracy circle as a map layer | 7 | yes | part |
| P2-06 | Route line rendering: casing + fill, progress-aware 'passed' dimming (line-gradient), traffic-coloured segments, unselected alternatives, tap-to-select, ETA labels on alternatives (declutter in Rust) | 8 | yes | part |
| P2-07 | Map pins: the nine `assets3d` billboard pins (police, hazard, accident, jam, closure, camera, gas, parking, destination) drawn unrotated at their anchor, contact shadow as a map-aligned circle layer (`circle-pitch-alignment: map`), clustering, zoom visibility, pop-in animation from the motion tokens; home/work/favourite/search pins added to the same pipeline | 6 | yes | part |
| P2-08 | `:location`: provider abstraction (Fused vs raw GNSS), permission state machine, rotation-vector/accelerometer/gyro inputs, mock-location flagging, accuracy filtering, adaptive rates, car-GPS hook; emits protobuf LocationSample | 8 | yes | part |
| P2-09 | Navigation foreground service (location type), ETA notification, Android 14+ compliance, background-location justification flow | 4 | yes | done |
| P2-10 | Gesture & rendering tuning: tile cache sizing, overdraw audit, 'map pan' Macrobenchmark with p95 gate | 4 | yes | — |
| P2-11 | Auto day/night (time, sunrise/sunset, ambient light) via style `global-state` toggle (no style reload) | 3 | yes | part |
| P2-13 | Vehicle skins: sedan, taxi and SUV from `assets3d` as on-demand asset packs (Play Asset Delivery), skin picker with live preview, hatch and van rendered with the same pipeline, per-skin licence entry | 6 | no | — |
| P2-12 | Offline regions v0: download bbox/zoom subset of PMTiles + routing tiles; storage manager UI | 6 | no | — |

- **P2-01** — MapLibre 13.7.1 lives in `:app`; no separate `:map` module, no frame-stats hook.
- **P2-03** — `scripts/fetch-dev-tiles.sh` pulls a KL extract. No Planetiler profile, no object storage or CDN, no weekly refresh.
- **P2-04** — `MapController` does follow/overview/center-on-me and the camera pitch presets. No speed-adaptive zoom, no HUD inset API.
- **P2-05** — Nearest pitch bucket and nearest of 24 yaws from the Blender sheets, with the sprite rotated by the remaining fraction of a bucket. No cross-bucket blending, no dead-reckoned interpolation, no accuracy circle.
- **P2-06** — Casing, fill, the greyed passed part and the alternatives drawn as one set under the chosen route. A grey line can now be tapped on the map to choose it (screen-space segment distance, unit-tested), which is the same decision as tapping its row. No traffic-coloured segments and no ETA labels on the alternatives yet.
- **P2-07** — All nine billboard pins are wired: one symbol layer draws the set from a single GeoJSON document (lon-first, tested), a map-aligned circle layer carries the contact shadow, pins stay hidden below zoom 12, and each one pops in over ~200 ms from the motion tokens. Category results use them today — Fuel draws gas pins, Parking parking pins, police and speed cameras their own — the list frames the pins above the sheet, tapping a pin opens the place card, and the pins outlive the sheet so closing the list leaves the answer on the map. Still missing: clustering where pins overlap, and the hazard/jam/closure/accident pins have no feed to draw from yet (they need the traffic source in P4).
- **P2-08** — Raw `LocationManager` fixes with a permission gate. No fused provider, rotation vectors, mock flagging or adaptive rates.
- **P2-09** — `NavService` is a `location`-type foreground service with a silent navigation notification (instruction, distance left, progress, Stop action, tap to open). Guidance, voice and the notification keep running with the screen off, verified on the emulator with the display dozing. No ETA clock in the notification yet.
- **P2-11** — `ThemeMode` cycles Auto/Day/Night: Auto is light between 06:30 and 19:00 (tropical sunrise and sunset, no summer to track), the manual modes are remembered across restarts, and the switch re-colours both the Compose theme and the map. Changing the mode still reloads the style rather than toggling `global-state`.
- **P2-13** — Hatch and van are not rendered; no skin picker.

### P3 · Search, places & routing

*Exit criterion:* Type a destination, see a place card, pick among routes, start.

11 tasks, 72 pd planned, 43 pd left. 0 done, 8 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P3-01 | Search domain + UI: debounced autocomplete, category chips (gas, parking, food, coffee, shopping, hotel, hospital/pharmacy, bank, police, car services), recents, favourites (home/work/custom), around-you vs along-route | 10 | yes | part |
| P3-02 | Geocoding backend: Photon deployment, ranking tweaks (distance bias, language), reverse geocode, rate limits, cache | 6 | yes | part |
| P3-03 | POI data: OSM POI extraction → search index, opening hours parsing, category mapping (Overture as later enrichment) | 6 | no | part |
| P3-04 | Place card (location preview): name/address/distance/ETA, actions (Go, Save, Share, Call), photos slot | 6 | yes | part |
| P3-05 | Routing service on Valhalla: costing profiles (car, motorcycle, taxi/HOV), options (avoid tolls/highways/ferries/unpaved), ≤ 3 alternatives, response mapper to `Route` proto (polyline6, legs, maneuvers, lanes, speed limits, tolls) | 10 | yes | part |
| P3-06 | Route preview (trip overview): ≤ 3 routes with ETA/distance/toll, colour-coded alternatives, details sheet with turn list, 'start' CTA | 8 | yes | part |
| P3-07 | Route model in core (Rust): decode, simplify, spatial index, cumulative distances, maneuver anchors, speed-limit segments, lane arrays | 6 | yes | — |
| P3-08 | Favourites/recents storage (Room) + sync API | 8 | no | part |
| P3-09 | Deep links & intents: `geo:`, `google.navigation:`, `aize://`, `https://aize.app/ul?…` (mirrors public waze.com/ul format), App Links verification | 3 | yes | — |
| P3-10 | Share destination link + landing page | 5 | no | — |
| P3-11 | Units/locale: km/mi, 12/24 h, number formats, right-hand/left-hand traffic cues, country packs for speed-limit defaults | 4 | yes | part |

- **P3-01** — Debounced name search, twelve category chips served by the search service (fuel, food, cafe, parking, ATM, pharmacy, hospital, mall, hotel, prayer room, EV charging, toilets) answered nearest-first, and the last ten searches kept on the phone. No address geocoding, no along-route search.
- **P3-02** — Deliberate deviation: SQLite FTS5 over the OSM extract instead of a Photon deployment, because Photon needs Java and a large index. No reverse geocoding, cache or rate limits.
- **P3-03** — `kind` comes from OSM tags and drives ranking. No opening hours, no category taxonomy beyond the tag pair.
- **P3-04** — Tapping a search result opens a card with the name, kind and distance, and three actions: Directions (hands the place to the route chooser), Save (keeps it in the list that shows when search is empty) and Share (an OpenStreetMap link through the system share sheet). No address line, no photos slot, no Call.
- **P3-05** — Up to three routes per request, with the server's toll, motorway and ferry flags mapped into `Route.Summary`. Still `costing=auto` only: no motorcycle or taxi profile, no avoid-tolls/highways options, and lanes, speed limits and per-edge tolls are not in the response the tiles are built from.
- **P3-06** — After a destination is picked the app lists the routes it got (distance, time, the road you spend longest on, and Fastest/Shortest/Tolls/Motorway/Ferry badges) and starts the one you tap. A turn list (every maneuver with its distance, arrival excluded) opens from the bottom bar. The alternatives are drawn on the map too: solid grey under the chosen purple one, framed so the whole set sits above the chooser, the row on the map marked "On map", and the grey lines cleared the moment a route is picked or cancelled.
- **P3-07** — Route decoding is Kotlin; the Rust port is blocked on a toolchain.
- **P3-08** — Saved places and the last ten searches are kept on the device as JSON in SharedPreferences (saved places newest first, 50 at most, deduped by position) and listed when the search field is empty. No Room, no sync between devices.
- **P3-11** — Kilometres and 24-hour clock only.

### P4 · Navigation engine & voice

*Exit criterion:* It guides you by voice and recovers when you leave the route.

14 tasks, 110 pd planned, 77 pd left. 0 done, 8 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P4-01 | Core: map matching v1 — HMM over candidate segments in the route corridor; free-matching fallback via server `trace_attributes` when off-route | 12 | yes | — |
| P4-02 | Core: route-progress tracker — projection, distance to next maneuver, remaining distance/time, hysteresis, tunnels (dead reckoning), loops/U-turns | 8 | yes | part |
| P4-03 | Core: off-route detection & reroute policy — accuracy-aware thresholds, heading mismatch, debounce, request rate-limit, rejoin logic, better-route suggestions | 8 | yes | part |
| P4-04 | Core: guidance engine — maneuver timeline, speed-adaptive prepare/approach/now triggers, lane-guidance early display, roundabout exits, speed-limit & camera zones, arrival, parking-suggestion trigger | 10 | yes | part |
| P4-05 | ETA engine: free-flow + live + historical speeds, smoothing (update only when \|Δ\| ≥ 30 s or 5 %), arrival clock formatting | 6 | yes | part |
| P4-06 | UniFFI bindings + Kotlin `NavigationEngine` exposing `Flow<NavState>`; dedicated core thread; zero-copy byte payloads | 6 | yes | — |
| P4-07 | Navigation UI wiring: HUD ← NavState, lane view, next-next maneuver, recenter logic, speedometer + limit sign (OSM maxspeed + country defaults), traffic bar, camera warnings | 12 | yes | part |
| P4-08 | `:voice` engine: prompt catalogue (§8), scheduler (priority queue, de-dup, interruption rules), audio focus + ducking (navigation-guidance usage), BT/car routing, modes (off/alerts/brief/smart/full), TTS fallback with prefetch cache | 12 | yes | part |
| P4-09 | Aize voice v1 recording: studio-recorded original prompt set (en + local language), loudness −16 LUFS, Opus 24 kbps mono | 8 | no | — |
| P4-10 | Voice-pack importer + custom-prompt recorder (Opus), manifest validation, per-pack licence field | 8 | no | — |
| P4-11 | Simulation harness: GPX/NMEA replay with speed multiplier, route-following simulator, scenarios (missed turn, tunnel, GPS jump, U-turn) | 6 | yes | part |
| P4-12 | Make navigation headless: engine + voice run in a foreground service independent of any Activity (prerequisite for Android Auto) | 4 | yes | part |
| P4-13 | Hot-path performance: allocation-free loop (dhat), criterion benches, PGO build job from recorded traces, battery script | 5 | no | — |
| P4-14 | Speed-limit & camera data pipeline: OSM maxspeed/enforcement nodes → tiles/route annotations; country default tables | 5 | no | — |

- **P4-01** — No map matching: the app projects onto the route it already has.
- **P4-02** — Windowed projection gives progress, distance to the next maneuver and the passed part. No hysteresis, tunnel dead reckoning, remaining time.
- **P4-03** — 40 m threshold, 3 strikes, 15 s cooldown, armed only after the first on-route fix. No accuracy awareness, heading mismatch, rejoin logic or better-route suggestion.
- **P4-04** — Maneuver timeline, next and next-next instructions, arrival within 30 m, and a speed-adaptive announcer (prepare at `max(150 m, speed x 8 s)`, imminent at 45 m, dedupe, 4 s quiet gap). No lane guidance, roundabout exit naming or camera zones.
- **P4-05** — `EtaEngine` scales Valhalla's free-flow time by the distance left, blends in live speed (clamped to +/-40 % so one traffic light cannot swing the clock), and publishes only when the estimate moves 30 s or 5 %. Arrival clock and the `12 min - 3:42 PM` line reach the banner and the notification. No historical speed profiles and no traffic bar.
- **P4-06** — Blocked: no Rust toolchain on the build VM.
- **P4-07** — Banner and follow camera. No lane view, speedometer, limit sign or traffic bar.
- **P4-08** — System TTS in `Voice.kt`: navigation-guidance usage, speech content type, transient-may-duck audio focus, `QUEUE_FLUSH` with a stable utterance id, and a two-prompt-per-maneuver scheduler in `GuidanceAnnouncer` (unit tested). No prompt catalogue, modes, Bluetooth routing or voice packs.
- **P4-11** — `scripts/replay-route.py` drives the emulator along a route at a chosen speed, straight from a GPX track or from the server's own Valhalla route, and can misbehave on purpose: miss a turn by N metres, stop reporting for N seconds (tunnel), or teleport the fix. NMEA import and a recorded-scenario library are still missing.
- **P4-12** — The hot loop (location, guidance, voice, notification) now runs in `NavService`, not in the Activity, and `NavSession` shares state with the UI. Still inside the app process, and no Android Auto.

### P5 · Live traffic & community

*Exit criterion:* Reports, alerts and traffic-aware routing from real probes.

12 tasks, 101 pd planned, 101 pd left. 0 done, 0 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P5-01 | Backend ingest: gRPC client-streaming probe upload, auth, rotating anonymous trip IDs, batching, validation (speed/accuracy bounds, mock rejection) | 10 | no | — |
| P5-02 | Traffic aggregator: probes → edge IDs (matcher), per-edge speed (t-digest medians over 2/5/15-min windows), k ≥ 5 distinct devices, jam detection, output Valhalla live-traffic tiles + vector overlay | 15 | no | — |
| P5-03 | Reports service: create/confirm/dismiss/comment, PostGIS + S2/H3 index, TTL per type, reputation weighting, dedup/clustering, moderation queue, rate limits | 12 | yes | — |
| P5-04 | Alert fan-out: viewport + route-corridor queries, delta streaming (protobuf), ETag/backoff | 6 | yes | — |
| P5-05 | Client report flow: menu grid → subtype → details (≤ 3 taps), voice report, photo attach, confirm/'still there?' prompts, offline queue | 12 | yes | — |
| P5-06 | Client alerts on route: look-ahead (R-tree on route buffer), alert pill pop-in (token timings), voice prompt, dismiss gestures, 'saves N min, avoids closure' reroute card | 8 | yes | — |
| P5-07 | Client traffic layer + traffic-aware routing/ETA hookup; coloured route segments; traffic bar | 6 | no | — |
| P5-08 | Probe uploader: batching (5–10 s), WorkManager fallback, battery/network constraints, privacy trimming (drop first/last 200 m or 30 s), opt-out | 6 | no | — |
| P5-09 | Moderation & anti-abuse: velocity checks, reputation, spatial-temporal consensus, optional Play Integrity, admin console | 8 | no | — |
| P5-10 | Gamification v0: points for reports/confirmations, levels, original avatars/vehicle icons | 8 | no | — |
| P5-11 | Load & chaos tests: 50 k concurrent probes, report storms, region fail-over; cost model | 6 | no | — |
| P5-12 | Community guidelines, report taxonomy & icons, appeals flow | 4 | yes | — |

The MVP part is small: report a hazard (P5-03, P5-05), see alerts on your route (P5-04, P5-06), and the taxonomy behind both (P5-12). The expensive half is the traffic engine — probe upload, map matching to edges, aggregation with k-anonymity, live-traffic tiles (P5-01, P5-02) — which needs a real backend and PostGIS, and only pays off with enough drivers. Do the MVP half first and treat traffic as a separate project.

### P6 · Planning, sharing & accounts

*Exit criterion:* Plan a drive, share an ETA, keep history.

7 tasks, 53 pd planned, 53 pd left. 0 done, 0 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P6-01 | Accounts: OIDC, passkeys via Credential Manager, guest mode, delete-account/export flows | 10 | no | — |
| P6-02 | Planned drives: manual create + optional calendar (scoped permission), leave-time notifications from traffic forecast | 10 | no | — |
| P6-03 | ETA sharing: live link, viewer web page, expiry, privacy controls, arrival notification | 10 | no | — |
| P6-04 | History & drive stats, favourites sync polish | 6 | no | — |
| P6-05 | Notifications: channels (navigation, reminders, social), FCM/UnifiedPush | 4 | no | — |
| P6-06 | Parking, gas prices & EV: POI sources, gas-type & connector preferences | 10 | no | — |
| P6-07 | Inbox (system messages) + in-app feedback | 3 | no | — |

Optional for an MVP. Guest-only keeps the privacy work small; accounts only earn their place if you want ETA sharing or planned drives.

### P7 · Android Auto

*Exit criterion:* The same guidance on the car screen.

5 tasks, 36 pd planned, 36 pd left. 0 done, 0 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P7-01 | `:auto` module: CarAppService with `androidx.car.app.category.NAVIGATION`, Session, NavigationTemplate + MapWithContentTemplate screens, NavigationManager metadata | 12 | no | — |
| P7-02 | Surface rendering via SurfaceCallback into MapLibre, car insets/sizes | 8 | no | — |
| P7-03 | Car input: search, favourites, quick report actions within driver-distraction limits | 6 | no | — |
| P7-04 | Car audio/GPS: guidance on car speakers, car-GPS source | 4 | no | — |
| P7-05 | Quality checklist (navigation category), DHU test plan, Play review prep | 6 | no | — |

Cannot start until navigation runs headless (P4-12). Also needs a Desktop Head Unit test plan and a Play review for the navigation category, so budget review time, not just build time.

### P8 · Polish, accessibility & performance

*Exit criterion:* Holds up on real devices, in every language, at every font size.

8 tasks, 48 pd planned, 48 pd left. 0 done, 0 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P8-01 | Animation QA against motion spec: frame-time traces per transition, fix deviations | 6 | no | — |
| P8-02 | Haptics + original earcon set (ping, report, points, mic) | 5 | no | — |
| P8-03 | Tablets/foldables/landscape (window-size classes) | 6 | no | — |
| P8-04 | Localisation: en, ms, id, zh + RTL (ar/he) QA | 8 | no | — |
| P8-05 | Accessibility audit (TalkBack, Switch Access, font scale 2.0) | 5 | no | — |
| P8-06 | Size/startup hardening: startup profile + baseline profile regeneration, R8 full mode, resource shrinking, per-ABI AAB, image/audio audit | 8 | no | — |
| P8-07 | Battery pass: location rates, wake-locks, idle render cap, sensor batching | 6 | no | — |
| P8-08 | Memory pass: LeakCanary, sprite/bitmap budgets, ANR watch | 4 | no | — |

Every task here needs a real device and the performance budgets from P0-09 to measure against. Running this before P0-09 is guesswork.

### P9 · Hardening & launch

*Exit criterion:* In the Play Store, with the evidence to defend it.

7 tasks, 48 pd planned, 48 pd left. 0 done, 0 part-done.

| Task | What | pd | MVP | Status |
|---|---|---|---|---|
| P9-01 | Security review: threat model, MASVS-L1 checklist, API authz tests, rate limits, secrets management | 8 | no | — |
| P9-02 | Privacy: DPIA, retention jobs, export/delete endpoints, consent logs, privacy labels | 6 | no | — |
| P9-03 | Play Console: data-safety form, foreground-service & background-location declarations (+video), listing, content rating | 4 | no | — |
| P9-04 | Observability & SLOs: dashboards, alerts, runbooks, on-call | 6 | no | — |
| P9-05 | Closed beta (200) → open beta; feedback loop; crash-free ≥ 99.5 % gate | 10 | no | — |
| P9-06 | Field-test campaign: 50 drives across road types; metrics report (match accuracy, false reroutes, ETA error, battery) | 8 | no | — |
| P9-07 | Launch: site, press kit, support docs, community guidelines | 6 | no | — |

The Play Console work (data-safety form, foreground-service and background-location declarations with video) is tedious and unforgiving; start it at M4, not at the end.

## Infrastructure as it stands

| What | Where | Notes |
|---|---|---|
| Routing + search | Small VM, permanent link | Valhalla 3.9.1 with the full Malaysia/Singapore/Brunei graph (735 tiles, 652 MB) and the 88 MB FTS5 search index, three systemd units behind one port |
| Build machine | XL VM | Android SDK 37, Gradle 9.8.2, Blender 4.5.9, emulator AVD `api34` |
| Source | `github.com/ejjat0909/Aize` | `main`, debug APKs shared as assets rather than committed |

## Decisions this plan is waiting on

- **Where the server lives, for good** — Decided: a Small VM with an always-on link, about $5 per 30 days. Revisit only if you want a real host with a domain and TLS.
- **Do you want the Rust core?** — The plan has `aize-core` in Rust behind UniFFI for map matching and the guidance engine. It needs a Rust toolchain and NDK on the build machine. Kotlin alone can carry M1 and M2; Rust matters from P4-01 and P5-02 onwards, where the maths gets heavy.
- **Offline or online only?** — Offline regions (P2-12) change the data pipeline, the app size and the store listing. Worth deciding before the tile pipeline is hardened in P2-03.
- **Accounts at all?** — P6 is entirely optional for an MVP. Guest-only keeps the privacy story simple and removes the DPIA work in P9-02, but also removes ETA sharing and sync.
- **How far do you want to go on voice?** — System TTS is a day of work; the recorded Aize voice set is a studio booking plus 51 prompts in two languages.

## Blockers on this machine

- **No Docker** — Planetiler and Photon have no images to run here. Routing and search were built without them; own tiles (P2-03) and a Photon deployment (P3-02) still need either Docker or a native build.
- **No Rust, no NDK, no JDK 21** — P4-06, P3-07 and all of `aize-core` are blocked. The build VM has JDK 17, which the project targets, so this costs nothing today.
- **One emulator, software rendering** — Every performance number so far is from swiftshader. P0-09 and the P8 passes need a real device.
- **Disk** — The build VM runs at about 86% full with the emulator images, the Android SDK, the routing tiles and the search index on it. A clean build needs roughly 2 GB free.

## Definition of done for the whole app

1. A signed release AAB on an internal, then open, Play track.
2. A drive of at least 30 minutes on a real phone with voice, lane guidance and no false reroutes.
3. Crash-free sessions above 99.5% over the beta.
4. Frame time inside budget on a mid-range device (P0-09 budgets, ratcheted).
5. Search and routing that answer in under a second for the pilot region, on the permanent server.
6. Privacy: no location leaves the device except to the user's own server; DPIA and data-safety form done.
7. Every generated artefact reproducible from the repo: design tokens, 3D sprites, tiles, index.

