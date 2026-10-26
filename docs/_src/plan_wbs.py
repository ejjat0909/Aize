#!/usr/bin/env python3
"""Aize work-breakdown structure (single source of truth).

Renders into docs/02-aize-build-plan.md (replaces the {{WBS}} and {{WBS_SUMMARY}} markers of the template)
and writes docs/backlog.csv (importable into GitHub Projects/Jira).

Estimates are person-days (pd) of one experienced engineer, ±40 %, excluding holidays/meetings.
mvp=True marks the smallest scope that deserves the name "Aize" (see plan §1).
Roles: AND Android/Kotlin · RST Rust core · BE backend · OPS devops/data pipelines · DES design · AUD audio · QA test · PM product/legal
usage: plan_wbs.py TEMPLATE.md OUT.md OUT_BACKLOG.csv TOKENS.json CONTRAST.md
"""
import csv
import os
import sys

PHASES = [
    ("P0", "Foundations & decisions", "W0–W2", "Everything needed so feature work never waits on tooling, data, or legal.",
     "Walking skeleton runs in CI: purple MapLibre map + live location puck + a Valhalla route drawn; baseline perf numbers recorded; ADRs merged."),
    ("P1", "Design system & app shell", "W2–W5", "The Aize look, feel and motion exist as reusable, tested components before any screen is built.",
     "Component catalogue app + screenshot tests green in light/dark/1.3× font; onboarding & permission flows demo-able; contrast gate in CI."),
    ("P2", "Map & location", "W4–W8", "A map that pans/zooms at 60 fps on a mid-range phone and a location pipeline that is accurate and frugal.",
     "p95 frame time ≤ 16.7 ms during pan/zoom on the reference mid-range device; puck/route/pins render correctly day & night; location survives screen-off for 30 min."),
    ("P3", "Search, places & routing", "W7–W12", "From 'where to?' to a chosen route: search, place card, route alternatives, deep links.",
     "A user can search, preview 3 routes with ETAs and tap Go; geo:/google.navigation:/aize:// links work; search p95 ≤ 300 ms server-side."),
    ("P4", "Navigation engine & voice", "W10–W16", "Turn-by-turn that is correct, calm and audible: matching, progress, reroute, lanes, prompts, simulator.",
     "50 recorded drives replay with ≥ 98 % on-route matching, ≤ 1 false reroute per 100 km, nav loop ≤ 5 ms p95; full voice guidance incl. ducking; simulator mode."),
    ("P5", "Live traffic & community", "W14–W22", "The Waze-like heart: probe-based traffic, user reports, alerts on route, reroute suggestions.",
     "Reports created/confirmed/expired end-to-end; alerts pop on route with voice; probe → traffic tile latency ≤ 90 s p95; abuse controls active."),
    ("P6", "Planning, sharing & accounts", "W20–W26", "Make it a daily driver: accounts, planned drives, ETA sharing, history, notifications.",
     "Account + sync live; ETA share link opens a live page; planned-drive 'leave now' notification fires correctly."),
    ("P7", "Android Auto", "W22–W28", "Same navigation core on the car screen using the Car App Library.",
     "Passes Android Auto navigation quality checks in the Desktop Head Unit; route preview, guidance, search, reports usable from the car."),
    ("P8", "Polish, accessibility & performance hardening", "W24–W30", "Every animation matches the motion spec; every budget in §9 is met; every locale is checked.",
     "All CI perf gates green on 3 reference devices; TalkBack audit clean; AAB per-ABI download ≤ 45 MB."),
    ("P9", "Hardening & launch", "W28–W34", "Security, privacy, store compliance, field tests, beta, launch.",
     "Closed beta crash-free ≥ 99.5 %, field-test report accepted, store listings approved, runbooks + on-call ready."),
]

# id, title, roles, days, mvp, deps, done-when
T = [
    # ---------------------------------------------------------------- P0
    ("P0-01", "Decision workshop: pilot region, minSdk, ABIs, repo licence, brand assets, domain, monetisation stance → ADR files", "PM", 2, True, [], "ADR-001…ADR-006 merged in docs/adr"),
    ("P0-02", "Monorepo scaffold: Gradle (KTS + version catalog), Rust workspaces (core, backend), buf/protobuf module, docs, design", "AND/RST", 3, True, ["P0-01"], "`./gradlew assembleDebug` and `cargo test --workspace` pass from a clean clone"),
    ("P0-03", "Pin toolchains: JDK 21, AGP, Kotlin 2.x + Compose compiler, NDK (≥ r27), Rust stable + android targets, cargo-ndk, buf, Valhalla/Planetiler/Photon container images", "AND/RST/OPS", 2, True, ["P0-02"], "`docs/dev-setup.md` reproduces the environment in < 30 min on a fresh machine"),
    ("P0-04", "CI: lint (ktlint/detekt, clippy, rustfmt), unit tests, assemble, cargo-deny (licences), dependency review, caching", "OPS", 3, True, ["P0-02"], "PR checks < 12 min; red on any licence violation"),
    ("P0-05", "Design-token pipeline: tokens JSON (exists: design/tokens) → Compose theme + MapLibre palette; contrast audit as CI gate", "AND/DES", 3, True, ["P0-02"], "Changing a token changes app + map; CI fails if a required contrast pair < threshold"),
    ("P0-06", "Legal baseline: third-party licence inventory + NOTICE, trademark/name clearance for 'Aize' and logo, privacy-policy skeleton, 'no Waze assets' policy + checker script", "PM", 3, True, ["P0-01"], "Clearance memo filed; `scripts/check-no-third-party-assets` runs in CI"),
    ("P0-07", "Data pipeline v0 for the pilot region: OSM extract → Planetiler → PMTiles; Valhalla tile build; Photon import; docker-compose dev stack", "OPS/BE", 5, True, ["P0-03"], "`docker compose up` serves tiles, routes and geocodes the pilot region locally"),
    ("P0-08", "Walking skeleton: Compose app + MapLibre purple style + location puck + hard-coded Valhalla route drawn", "AND", 5, True, ["P0-05", "P0-07"], "Debug APK built by CI shows the route on a purple map"),
    ("P0-09", "Performance harness: Macrobenchmark module, Baseline-Profile generator module, Perfetto capture scripts, JankStats in debug; first numbers committed", "AND", 3, True, ["P0-08"], "`benchmarks/results/baseline.json` committed; gate script compares future runs"),
    ("P0-10", "Crash/telemetry scaffolding (privacy-first, opt-in), remote feature-flag client, build-config for staging/prod", "AND/BE", 2, False, ["P0-02"], "Flags toggle a hidden screen; crash test event arrives"),
    ("P0-11", "Security baseline: secrets handling (no keys in repo), signing config, dependency pinning, SAST in CI", "OPS", 2, False, ["P0-04"], "Secret scanner + SAST required checks"),
    # ---------------------------------------------------------------- P1
    ("P1-01", "Compose theme from tokens (light/dark/dynamic-off), typography (Figtree subset + Roboto fallback), shapes, elevation, spacing", "AND", 4, True, ["P0-05"], "Theme preview matches design/preview; fonts licence-checked"),
    ("P1-02", "Icon set v1 (~60): nav arrows, lane arrows, report types, POI categories, UI glyphs — SVG → ImageVector on a 24 dp grid", "DES", 8, True, ["P0-05"], "Icons delivered as SVG + generated Kotlin; none derived from third-party sets with incompatible licences"),
    ("P1-03", "Component library v1: buttons (S/M/L radii 18/24/32), icon buttons, chips/pills, cards, dialogs, bottom sheet (peek/half/full, 150 ms slide), snackbar, text fields, switches, list rows, segmented control, tooltip", "AND", 10, True, ["P1-01"], "All components have previews, a11y labels, 48 dp targets"),
    ("P1-04", "Navigation HUD components (stateless): instruction banner + lane strip, ETA bar (compact/expanded), speed bubble + limit sign, report FAB, recenter button, compass, alert pill (pop-in), arrival card", "AND/DES", 14, True, ["P1-03"], "Each renders from a plain state object; no state held inside"),
    ("P1-05", "Motion kit: easing/duration tokens as AnimationSpecs, popIn/sheet/page transitions, reduced-motion replacement, RenderThread-friendly (graphicsLayer) variants", "AND", 3, True, ["P1-01"], "All animations read tokens; reduced-motion toggle verified"),
    ("P1-06", "Original Lottie/Rive assets: splash, report button idle/press, points/confetti, loaders (skeleton), mic listening/speaking states", "DES", 8, False, ["P1-05"], "Assets ≤ 40 KB each, 60 fps on mid-range device in benchmark"),
    ("P1-07", "Design-catalogue module + screenshot tests (Paparazzi/Roborazzi) for every component × light/dark × font-scale 1.3 × RTL", "AND", 5, True, ["P1-04"], "Golden images checked in; CI fails on pixel diffs"),
    ("P1-08", "App shell: single-Activity + type-safe Navigation, Android 12 splash + animated icon, onboarding, permission rationale flows (precise location → background → notifications → mic), consent screen", "AND", 8, True, ["P1-03"], "Cold-start to onboarding ≤ 1.2 s on reference mid-range device"),
    ("P1-09", "Settings framework: declarative tree DSL (id path, type, search, deep link), DataStore persistence; seed with the v1 subset (Appendix C)", "AND", 5, True, ["P1-03"], "Adding a setting = one DSL entry; settings searchable"),
    ("P1-10", "Accessibility baseline: TalkBack semantics, large fonts, colour-blind-safe traffic cues (icon/pattern + colour), contrast gate, reduced motion", "AND/DES", 5, True, ["P1-04"], "Axe/Accessibility Scanner clean on catalogue screens"),
    ("P1-12", "3D asset pipeline in CI: pinned, checksum-verified Blender 4.5 LTS; `assets3d/build_all.sh`; the verification gates (camera anchor/pitch, clip, brand colour, WebP round-trip, silhouette/raised/image/pop, size budget) as a required check; sprite sheets and manifests published as build artifacts", "OPS/AND", 3, True, ["P0-04", "P1-01"], "A token change re-renders the pointer family in CI and the gates are green; `assets3d/RESULTS.md` regenerates"),
    ("P1-11", "i18n pipeline: Android resources + Weblate/Crowdin, pseudo-locales, RTL enabled (supportsRtl=true), plural/units formatting", "AND", 3, False, ["P1-08"], "App runs in en, ms + en-XA pseudo locale without truncation"),
    # ---------------------------------------------------------------- P2
    ("P2-01", "`:map` module: MapLibre Native (SurfaceView mode, Vulkan/OpenGL artifact decision), lifecycle, style loading, tile cache config, frame-stats hook", "AND", 5, True, ["P0-08"], "Map survives rotation/background; frame stats exposed to benchmarks"),
    ("P2-02", "Style generator: day/night MapLibre style JSON from tokens — categories analogous to the 49 Waze layers (freeway/primary/secondary/street/alley/private/trail/ramp, rail, ferry, water, parks, buildings, parking, cities, labels + shields) with zoom-interpolated width/colour/label size; golden-image tests", "AND/DES", 8, True, ["P2-01", "P0-05"], "Style renders without warnings; screenshots of 6 reference cities approved by design"),
    ("P2-03", "Tile pipeline hardening: Planetiler profile (only needed layers), PMTiles on object storage + CDN, attribution (OSM ODbL), weekly refresh job", "BE/OPS", 5, True, ["P0-07"], "Tiles for the region ≤ 1.5 GB, p95 tile TTFB ≤ 80 ms from CDN"),
    ("P2-04", "`MapController` API (mirrors observed Waze camera API): centerOnMe/Position, showOverview(route), compass modes, margins/insets for HUD, user-location offset, zoom in/out, speed-adaptive zoom/tilt, animated with silky easings; camera presets (overview 0 deg, browse 30, drive 45, navigate 60) are the pointer sprite's pitch buckets, so every steady state is on-grid", "AND", 6, True, ["P2-01", "P1-05"], "Camera never fights user gestures; insets verified with HUD on 3 screen sizes"),
    ("P2-05", "Pointer overlay (`PointerOverlay` composable) over the map: arrow / puck / car-skin sprites from `assets3d` - two pitch buckets warped to the true pitch/yaw by one affine matrix (see `assets3d/README.md#runtime-algorithm`), blended by pitch, dissolve on a heading-bucket change; positioned by the map projection; 60 fps dead-reckoned interpolation between GPS fixes; accuracy circle as a map layer", "AND", 7, True, ["P2-01", "P1-12", "P1-05"], "Matches `assets3d/tools/simulate_runtime.py` on its golden views within 0.5 dp; draw cost <= 0.3 ms p95; no allocation per frame (allocation tracker)"),
    ("P2-06", "Route line rendering: casing + fill, progress-aware 'passed' dimming (line-gradient), traffic-coloured segments, unselected alternatives, tap-to-select, ETA labels on alternatives (declutter in Rust)", "AND/RST", 8, True, ["P2-01", "P3-07"], "3 routes render and select smoothly; labels never overlap"),
    ("P2-07", "Map pins: the nine `assets3d` billboard pins (police, hazard, accident, jam, closure, camera, gas, parking, destination) drawn unrotated at their anchor, contact shadow as a map-aligned circle layer (`circle-pitch-alignment: map`), clustering, zoom visibility, pop-in animation from the motion tokens; home/work/favourite/search pins added to the same pipeline", "AND/DES", 6, True, ["P2-01", "P1-12"], "1 000 pins pan at 60 fps; pins keep their screen size and orientation at every pitch and bearing"),
    ("P2-08", "`:location`: provider abstraction (Fused vs raw GNSS), permission state machine, rotation-vector/accelerometer/gyro inputs, mock-location flagging, accuracy filtering, adaptive rates, car-GPS hook; emits protobuf LocationSample", "AND", 8, True, ["P0-02"], "Works with permission changes mid-trip; battery budget test passes"),
    ("P2-09", "Navigation foreground service (location type), ETA notification, Android 14+ compliance, background-location justification flow", "AND", 4, True, ["P2-08"], "Survives 60 min screen-off on 3 OEM skins"),
    ("P2-10", "Gesture & rendering tuning: tile cache sizing, overdraw audit, 'map pan' Macrobenchmark with p95 gate", "AND", 4, True, ["P2-05", "P2-07"], "p95 frame ≤ 16.7 ms (60 Hz) on reference mid-range device"),
    ("P2-11", "Auto day/night (time, sunrise/sunset, ambient light) via style `global-state` toggle (no style reload)", "AND", 3, True, ["P2-02"], "Switch < 100 ms, no flash"),
    ("P2-13", "Vehicle skins: sedan, taxi and SUV from `assets3d` as on-demand asset packs (Play Asset Delivery), skin picker with live preview, hatch and van rendered with the same pipeline, per-skin licence entry", "AND/DES", 6, False, ["P2-05"], "A skin downloads on demand (<= 4 MB at the device's density) and replaces the pointer without a restart"),
    ("P2-12", "Offline regions v0: download bbox/zoom subset of PMTiles + routing tiles; storage manager UI", "AND/BE", 6, False, ["P2-03"], "Region works in airplane mode (map + search by saved places)"),
    # ---------------------------------------------------------------- P3
    ("P3-01", "Search domain + UI: debounced autocomplete, category chips (gas, parking, food, coffee, shopping, hotel, hospital/pharmacy, bank, police, car services), recents, favourites (home/work/custom), around-you vs along-route", "AND", 10, True, ["P1-03", "P3-02"], "Typing → first result ≤ 250 ms p95 end-to-end; offline recents work"),
    ("P3-02", "Geocoding backend: Photon deployment, ranking tweaks (distance bias, language), reverse geocode, rate limits, cache", "BE", 6, True, ["P0-07"], "Top-3 hit-rate ≥ 90 % on 200 hand-labelled local queries"),
    ("P3-03", "POI data: OSM POI extraction → search index, opening hours parsing, category mapping (Overture as later enrichment)", "BE/OPS", 6, False, ["P3-02"], "Category search returns relevant POIs within 5 km in < 200 ms"),
    ("P3-04", "Place card (location preview): name/address/distance/ETA, actions (Go, Save, Share, Call), photos slot", "AND", 6, True, ["P3-01"], "Opens < 150 ms from result tap; a11y labels"),
    ("P3-05", "Routing service on Valhalla: costing profiles (car, motorcycle, taxi/HOV), options (avoid tolls/highways/ferries/unpaved), ≤ 3 alternatives, response mapper to `Route` proto (polyline6, legs, maneuvers, lanes, speed limits, tolls)", "BE", 10, True, ["P0-07"], "p95 route (≤ 50 km) ≤ 400 ms; alternatives ≥ 20 % different"),
    ("P3-06", "Route preview (trip overview): ≤ 3 routes with ETA/distance/toll, colour-coded alternatives, details sheet with turn list, 'start' CTA", "AND", 8, True, ["P2-06", "P3-05"], "Selecting a route animates camera with `silkyIn` ≤ 500 ms"),
    ("P3-07", "Route model in core (Rust): decode, simplify, spatial index, cumulative distances, maneuver anchors, speed-limit segments, lane arrays", "RST", 6, True, ["P0-02"], "Property tests; decode 100 km route ≤ 3 ms"),
    ("P3-08", "Favourites/recents storage (Room) + sync API", "AND/BE", 8, False, ["P3-01"], "Edits on device A appear on device B ≤ 5 s"),
    ("P3-09", "Deep links & intents: `geo:`, `google.navigation:`, `aize://`, `https://aize.app/ul?…` (mirrors public waze.com/ul format), App Links verification", "AND", 3, True, ["P3-06"], "Intent test matrix green; assistant launch works"),
    ("P3-10", "Share destination link + landing page", "BE/AND", 5, False, ["P3-09"], "Link opens app or web fallback"),
    ("P3-11", "Units/locale: km/mi, 12/24 h, number formats, right-hand/left-hand traffic cues, country packs for speed-limit defaults", "AND/RST", 4, True, ["P3-07"], "Unit tests per locale; voice uses locale units"),
    # ---------------------------------------------------------------- P4
    ("P4-01", "Core: map matching v1 — HMM over candidate segments in the route corridor; free-matching fallback via server `trace_attributes` when off-route", "RST", 12, True, ["P3-07"], "≥ 98 % correct segment on 50-drive corpus; ≤ 2 ms per fix p95"),
    ("P4-02", "Core: route-progress tracker — projection, distance to next maneuver, remaining distance/time, hysteresis, tunnels (dead reckoning), loops/U-turns", "RST", 8, True, ["P4-01"], "Replay corpus produces monotonic progress; tunnel test passes"),
    ("P4-03", "Core: off-route detection & reroute policy — accuracy-aware thresholds, heading mismatch, debounce, request rate-limit, rejoin logic, better-route suggestions", "RST", 8, True, ["P4-02"], "≤ 1 false reroute / 100 km; reroute decision ≤ 1.5 s after deviation"),
    ("P4-04", "Core: guidance engine — maneuver timeline, speed-adaptive prepare/approach/now triggers, lane-guidance early display, roundabout exits, speed-limit & camera zones, arrival, parking-suggestion trigger", "RST", 10, True, ["P4-02"], "Trigger distances unit-tested at 30/60/100/130 km/h"),
    ("P4-05", "ETA engine: free-flow + live + historical speeds, smoothing (update only when |Δ| ≥ 30 s or 5 %), arrival clock formatting", "RST", 6, True, ["P4-02"], "ETA never oscillates > 1 min/min in replays"),
    ("P4-06", "UniFFI bindings + Kotlin `NavigationEngine` exposing `Flow<NavState>`; dedicated core thread; zero-copy byte payloads", "RST/AND", 6, True, ["P4-01"], "Location-in → state-out ≤ 5 ms p95 on reference device"),
    ("P4-07", "Navigation UI wiring: HUD ← NavState, lane view, next-next maneuver, recenter logic, speedometer + limit sign (OSM maxspeed + country defaults), traffic bar, camera warnings", "AND", 12, True, ["P4-06", "P1-04"], "No jank (p99 ≤ 24 ms) during 30-min simulated drive"),
    ("P4-08", "`:voice` engine: prompt catalogue (§8), scheduler (priority queue, de-dup, interruption rules), audio focus + ducking (navigation-guidance usage), BT/car routing, modes (off/alerts/brief/smart/full), TTS fallback with prefetch cache", "AND/RST", 12, True, ["P4-04"], "No overlapping prompts in 100-trip simulation; ducking verified with music apps"),
    ("P4-09", "Aize voice v1 recording: studio-recorded original prompt set (en + local language), loudness −16 LUFS, Opus 24 kbps mono", "AUD", 8, False, ["P4-08"], "Pack ≤ 1.5 MB, listening test ≥ 4/5 clarity"),
    ("P4-10", "Voice-pack importer + custom-prompt recorder (Opus), manifest validation, per-pack licence field", "AND", 8, False, ["P4-08"], "User-recorded pack plays; malformed pack rejected safely"),
    ("P4-11", "Simulation harness: GPX/NMEA replay with speed multiplier, route-following simulator, scenarios (missed turn, tunnel, GPS jump, U-turn)", "AND/RST", 6, True, ["P4-02"], "Demo mode runnable from debug menu; scenarios used in CI"),
    ("P4-12", "Make navigation headless: engine + voice run in a foreground service independent of any Activity (prerequisite for Android Auto)", "AND", 4, True, ["P4-06", "P2-09"], "Navigation continues with UI destroyed"),
    ("P4-13", "Hot-path performance: allocation-free loop (dhat), criterion benches, PGO build job from recorded traces, battery script", "RST", 5, False, ["P4-04"], "`aize-core` ≤ 3 % of one big core during guidance and whole-process CPU within the §9 budget"),
    ("P4-14", "Speed-limit & camera data pipeline: OSM maxspeed/enforcement nodes → tiles/route annotations; country default tables", "BE/RST", 5, False, ["P3-05"], "Limit shown on ≥ 85 % of pilot-region primary roads"),
    # ---------------------------------------------------------------- P5
    ("P5-01", "Backend ingest: gRPC client-streaming probe upload, auth, rotating anonymous trip IDs, batching, validation (speed/accuracy bounds, mock rejection)", "BE", 10, False, ["P0-07"], "10 k probes/s on one node, p99 ≤ 50 ms"),
    ("P5-02", "Traffic aggregator: probes → edge IDs (matcher), per-edge speed (t-digest medians over 2/5/15-min windows), k ≥ 5 distinct devices, jam detection, output Valhalla live-traffic tiles + vector overlay", "BE/RST", 15, False, ["P5-01", "P3-05"], "Probe → routable traffic ≤ 90 s p95; speed MAE ≤ 12 km/h vs ground truth"),
    ("P5-03", "Reports service: create/confirm/dismiss/comment, PostGIS + S2/H3 index, TTL per type, reputation weighting, dedup/clustering, moderation queue, rate limits", "BE", 12, True, ["P0-07"], "Nearby query p95 ≤ 60 ms with 1 M active reports"),
    ("P5-04", "Alert fan-out: viewport + route-corridor queries, delta streaming (protobuf), ETag/backoff", "BE", 6, True, ["P5-03"], "Alert visible on other devices ≤ 5 s p95"),
    ("P5-05", "Client report flow: menu grid → subtype → details (≤ 3 taps), voice report, photo attach, confirm/'still there?' prompts, offline queue", "AND", 12, True, ["P1-04", "P5-03"], "Median report time ≤ 4 s; works offline"),
    ("P5-06", "Client alerts on route: look-ahead (R-tree on route buffer), alert pill pop-in (token timings), voice prompt, dismiss gestures, 'saves N min, avoids closure' reroute card", "AND/RST", 8, True, ["P5-04", "P4-04"], "Alert appears at configured distance ±10 % at 30–130 km/h"),
    ("P5-07", "Client traffic layer + traffic-aware routing/ETA hookup; coloured route segments; traffic bar", "AND", 6, False, ["P5-02", "P4-05"], "ETA error ≤ 10 % on congested test routes"),
    ("P5-08", "Probe uploader: batching (5–10 s), WorkManager fallback, battery/network constraints, privacy trimming (drop first/last 200 m or 30 s), opt-out", "AND/RST", 6, False, ["P5-01"], "≤ 1.5 MB/h cellular; opt-out stops uploads immediately"),
    ("P5-09", "Moderation & anti-abuse: velocity checks, reputation, spatial-temporal consensus, optional Play Integrity, admin console", "BE", 8, False, ["P5-03"], "Spam test set blocked ≥ 95 %"),
    ("P5-10", "Gamification v0: points for reports/confirmations, levels, original avatars/vehicle icons", "AND/DES", 8, False, ["P5-05"], "Points ledger consistent; no dark patterns"),
    ("P5-11", "Load & chaos tests: 50 k concurrent probes, report storms, region fail-over; cost model", "BE/QA", 6, False, ["P5-02", "P5-04"], "SLO dashboard green under load"),
    ("P5-12", "Community guidelines, report taxonomy & icons, appeals flow", "PM/DES", 4, True, ["P5-03"], "Guidelines published; taxonomy mapped to icons"),
    # ---------------------------------------------------------------- P6
    ("P6-01", "Accounts: OIDC, passkeys via Credential Manager, guest mode, delete-account/export flows", "BE/AND", 10, False, ["P0-07"], "Sign-up → sync → delete works end-to-end"),
    ("P6-02", "Planned drives: manual create + optional calendar (scoped permission), leave-time notifications from traffic forecast", "AND/BE", 10, False, ["P6-01", "P5-07"], "Notification fires within ±2 min of computed leave time"),
    ("P6-03", "ETA sharing: live link, viewer web page, expiry, privacy controls, arrival notification", "AND/BE", 10, False, ["P6-01"], "Viewer updates ≤ 5 s; link revocable"),
    ("P6-04", "History & drive stats, favourites sync polish", "AND/BE", 6, False, ["P6-01"], "History can be disabled and wiped"),
    ("P6-05", "Notifications: channels (navigation, reminders, social), FCM/UnifiedPush", "AND/BE", 4, False, ["P6-01"], "Channel settings respected"),
    ("P6-06", "Parking, gas prices & EV: POI sources, gas-type & connector preferences", "AND/BE", 10, False, ["P3-03"], "Preferences filter results correctly"),
    ("P6-07", "Inbox (system messages) + in-app feedback", "AND", 3, False, ["P6-05"], "Message render + dismiss"),
    # ---------------------------------------------------------------- P7
    ("P7-01", "`:auto` module: CarAppService with `androidx.car.app.category.NAVIGATION`, Session, NavigationTemplate + MapWithContentTemplate screens, NavigationManager metadata", "AND", 12, False, ["P4-12"], "Runs in Desktop Head Unit; route + guidance visible"),
    ("P7-02", "Surface rendering via SurfaceCallback into MapLibre, car insets/sizes", "AND", 8, False, ["P7-01", "P2-01"], "30 fps stable on DHU; no leaks on connect/disconnect"),
    ("P7-03", "Car input: search, favourites, quick report actions within driver-distraction limits", "AND", 6, False, ["P7-01"], "No template violations in host logs"),
    ("P7-04", "Car audio/GPS: guidance on car speakers, car-GPS source", "AND", 4, False, ["P7-01"], "Prompts audible, source tagged `external`"),
    ("P7-05", "Quality checklist (navigation category), DHU test plan, Play review prep", "QA", 6, False, ["P7-03"], "All applicable car-quality items pass"),
    # ---------------------------------------------------------------- P8
    ("P8-01", "Animation QA against motion spec: frame-time traces per transition, fix deviations", "AND/DES", 6, False, ["P4-07"], "Every transition within ±1 frame of spec"),
    ("P8-02", "Haptics + original earcon set (ping, report, points, mic)", "AUD/DES", 5, False, ["P4-08"], "Earcons ≤ 80 KB total"),
    ("P8-03", "Tablets/foldables/landscape (window-size classes)", "AND", 6, False, ["P4-07"], "Layouts verified on 4 form factors"),
    ("P8-04", "Localisation: en, ms, id, zh + RTL (ar/he) QA", "QA", 8, False, ["P1-11"], "No truncation/overlap in screenshots"),
    ("P8-05", "Accessibility audit (TalkBack, Switch Access, font scale 2.0)", "QA", 5, False, ["P4-07"], "No blocking issues"),
    ("P8-06", "Size/startup hardening: startup profile + baseline profile regeneration, R8 full mode, resource shrinking, per-ABI AAB, image/audio audit", "AND", 8, False, ["P4-07"], "Cold start ≤ 1.2 s; download ≤ 45 MB"),
    ("P8-07", "Battery pass: location rates, wake-locks, idle render cap, sensor batching", "AND/RST", 6, False, ["P4-13"], "≤ 7 %/h with screen on (reference device)"),
    ("P8-08", "Memory pass: LeakCanary, sprite/bitmap budgets, ANR watch", "AND", 4, False, ["P4-07"], "RSS ≤ 300 MB during nav; no leaks in 1-h soak"),
    # ---------------------------------------------------------------- P9
    ("P9-01", "Security review: threat model, MASVS-L1 checklist, API authz tests, rate limits, secrets management", "BE/QA", 8, False, ["P5-09", "P6-01"], "No high/critical findings open"),
    ("P9-02", "Privacy: DPIA, retention jobs, export/delete endpoints, consent logs, privacy labels", "PM/BE", 6, False, ["P6-01"], "Retention verified by automated test"),
    ("P9-03", "Play Console: data-safety form, foreground-service & background-location declarations (+video), listing, content rating", "PM", 4, False, ["P9-02"], "Store review passed"),
    ("P9-04", "Observability & SLOs: dashboards, alerts, runbooks, on-call", "OPS", 6, False, ["P5-11"], "Game-day exercise completed"),
    ("P9-05", "Closed beta (200) → open beta; feedback loop; crash-free ≥ 99.5 % gate", "QA/PM", 10, False, ["P8-06"], "Gate met 14 days running"),
    ("P9-06", "Field-test campaign: 50 drives across road types; metrics report (match accuracy, false reroutes, ETA error, battery)", "QA", 8, False, ["P4-13", "P5-07"], "Targets in §12 met"),
    ("P9-07", "Launch: site, press kit, support docs, community guidelines", "PM", 6, False, ["P9-03"], "Public listing live"),
]

ids = {t[0] for t in T}
for t in T:
    for d in t[5]:
        assert d in ids, f"unknown dependency {d} in {t[0]}"
assert len(ids) == len(T), "duplicate task id"


def totals(rows):
    return sum(r[3] for r in rows)


def render():
    out, summ = [], []
    summ.append("| Phase | Weeks* | Tasks | MVP person-days | All person-days | Goal |")
    summ.append("|---|---|---:|---:|---:|---|")
    tot_all = tot_mvp = n_all = n_mvp = 0
    for pid, name, weeks, goal, exit_ in PHASES:
        rows = [t for t in T if t[0].startswith(pid + "-")]
        m = totals([r for r in rows if r[4]])
        a = totals(rows)
        tot_all += a
        tot_mvp += m
        n_all += len(rows)
        n_mvp += sum(1 for r in rows if r[4])
        summ.append(f"| **{pid}** {name} | {weeks} | {len(rows)} ({sum(1 for r in rows if r[4])} MVP) | {m} | {a} | {goal} |")
        out.append(f"### {pid} — {name}  ·  {weeks}")
        out.append("")
        out.append(f"**Goal.** {goal}  ")
        out.append(f"**Exit criteria.** {exit_}  ")
        out.append(f"**Effort.** {a} pd total, of which {m} pd MVP.")
        out.append("")
        for tid, title, roles, days, mvp, deps, done in rows:
            tag = " 🔹MVP" if mvp else ""
            dep = f" · needs {', '.join(deps)}" if deps else ""
            out.append(f"- [ ] **{tid}**{tag} {title}  ")
            out.append(f"  _{roles} · {days} pd{dep}_ → **Done when:** {done}")
        out.append("")
    summ.append(f"| **Total** | | {n_all} ({n_mvp} MVP) | **{tot_mvp}** | **{tot_all}** | |")
    summ.append("")
    summ.append("\\* Calendar weeks assume the 7-person team in §15 working in parallel; phases overlap on purpose (dependencies are listed per task).")
    # staffing table
    eff = 16  # effective person-days per person-month after meetings, reviews, context switching
    summ.append("")
    summ.append("| Scenario | People | Effective pd / month | MVP (months) | v1.0 public beta (months) |")
    summ.append("|---|---:|---:|---:|---:|")
    for label, p in (("Solo + AI pair-programming", 1), ("Small team", 3), ("Reference team (§15)", 7)):
        summ.append(f"| {label} | {p} | {p * eff} | {tot_mvp / (p * eff):.1f} | {tot_all / (p * eff):.1f} |")
    summ.append("")
    summ.append(f"Formula: months = person-days ÷ (people × {eff}). {eff} effective pd/person-month already discounts meetings, reviews and context switching (20 working days × 0.8). Estimates are ±40 %; the MVP/v1 split is in the task list. Parallelism is capped by dependencies, so the 7-person figure is a lower bound, not a promise.")
    return "\n".join(out), "\n".join(summ), tot_mvp, tot_all


def render_tokens(tokens_json, contrast_md):
    import json, re
    T_ = json.load(open(tokens_json))
    c = T_["color"]
    steps = [k for k in c["purple"]]
    pal = ["| Step | Purple (brand) | Lilac (secondary) | Mint (tertiary) | Neutral (lavender-tinted) |", "|---|---|---|---|---|"]
    for k in steps:
        pal.append(f"| {k} | `{c['purple'][k]}` | `{c['lilac'][k]}` | `{c['mint'][k]}` | `{c['neutral'][k]}` |")
    roles = ["primary", "onPrimary", "primaryContainer", "onPrimaryContainer", "secondary", "tertiary", "background", "onBackground", "surface", "onSurface", "surfaceVariant", "onSurfaceVariant", "outline", "outlineVariant", "error", "success", "warning", "info"]
    th = ["| Role | Light | Dark |", "|---|---|---|"] + [f"| `{r}` | `{T_['theme']['light'][r]}` | `{T_['theme']['dark'][r]}` |" for r in roles]
    fn = ["| Semantic | Light | Dark |", "|---|---|---|"]
    for k in T_["traffic"]["light"]:
        fn.append(f"| traffic · {k} | `{T_['traffic']['light'][k]}` | `{T_['traffic']['dark'][k]}` |")
    for k in T_["reports"]["light"]:
        fn.append(f"| report · {k.replace('_', ' ')} | `{T_['reports']['light'][k]}` | `{T_['reports']['dark'][k]}` |")
    mp = ["| Map element | Light | Dark |", "|---|---|---|"] + [f"| {k} | `{T_['map']['light'][k]}` | `{T_['map']['dark'][k]}` |" for k in T_["map"]["light"]]
    rt = ["| Route element | Light | Dark |", "|---|---|---|"] + [f"| {k} | `{T_['route']['light'][k]}` | `{T_['route']['dark'][k]}` |" for k in T_["route"]["light"]]
    line = re.search(r"\*\*(\d+)/(\d+) pairs pass; (\d+) required failure", open(contrast_md).read())
    cl = f"{line.group(1)}/{line.group(2)} contrast pairs pass ({line.group(3)} required failures)" if line else "see CONTRAST.md"
    return {"{{PALETTE_TABLE}}": "\n".join(pal), "{{THEME_TABLE}}": "\n".join(th), "{{FUNCTIONAL_TABLE}}": "\n".join(fn), "{{MAP_TABLE}}": "\n".join(mp), "{{ROUTE_TABLE}}": "\n".join(rt), "{{CONTRAST_LINE}}": cl}


def render_assets3d(summary_path):
    """Replacements for the 3D-asset section, generated from assets3d/dist/summary.json (never typed by hand)."""
    import json
    if not os.path.exists(summary_path):
        return {"{{ASSETS3D_TABLE}}": "_(run `bash assets3d/build_all.sh all` to generate the asset table)_", "{{ASSETS3D_QUALITY}}": ""}
    A = json.load(open(summary_path))["assets"]

    def fam(prefix):
        return {k: v for k, v in A.items() if k.startswith(prefix)}

    def kib(v, tier="xxhdpi"):
        return v["tiers_kib"].get(tier, 0)

    rows = ["| Family | Assets | Frames each | Size at 3x (xxhdpi) | Drawn as |", "|---|---|---|---:|---|"]
    point = {k: v for k, v in A.items() if k in ("arrow", "puck")}
    if point:
        rows.append("| Pointer | " + ", ".join(f"`{k}`" for k in point) + " | " + " / ".join(f"{v['frames']}" for v in point.values()) + " | " + " + ".join(f"{kib(v):,.0f} KiB" for v in point.values())
                    + " | two bracketing pitch buckets, one affine warp each, blended |")
    cars = fam("car_")
    if cars:
        v0 = next(iter(cars.values()))
        rows.append("| Vehicle skins | " + ", ".join(f"`{k}`" for k in cars) + f" | {v0['frames']} ({len(v0['pitches'])} pitches x {v0['yaws']} headings) | "
                    f"{min(kib(v) for v in cars.values()):,.0f}-{max(kib(v) for v in cars.values()):,.0f} KiB each | same; delivered as on-demand packs |")
    pins = fam("pin_")
    if pins:
        rows.append(f"| Map pins | {len(pins)} pins (" + ", ".join(k[4:] for k in pins) + f") | 1 | "
                    f"{min(kib(v) for v in pins.values()):,.0f}-{max(kib(v) for v in pins.values()):,.0f} KiB each | one cell, unrotated, contact shadow as a map layer |")

    q = ""
    ar = A.get("arrow", {}).get("reprojection") or {}
    im = ar.get("image")
    if ar and im:
        q += (f"For the **arrow**, the visible outline (the rim) of a reconstructed off-grid view is within {ar['base_worst_err_dp']:.2f} dp of its geometrically true position at every pitch and heading, "
              f"the image matches a true Blender render at {im['psnr_mean_db']:.1f} dB mean PSNR (worst view {im['psnr_min_db']:.1f} dB), "
              f"and the image change when the pitch crosses a bucket is {im.get('pitch_pop_rms_max', im['switch_pop_rms_max']):.4f} RMS. ")
    car_rp = [v["reprojection"] for k, v in A.items() if k.startswith("car_") and v.get("reprojection")]
    car_im = [c["image"]["psnr_mean_db"] for c in car_rp if c.get("image")]
    if car_rp and car_im:
        q += (f"**Cars are less exact**: {min(car_im):.0f}-{max(car_im):.0f} dB mean PSNR, with the wheels and underbody up to {max(c['base_worst_err_dp'] for c in car_rp):.1f} dp off in the single-bucket fallback, "
              "because a car has real parallax between its wheels and its roof that one re-projection plane cannot serve; a blend shows slight ghosting at glass, wheels and tail-lights "
              "(`assets3d/README.md`, section Cars).")
    return {"{{ASSETS3D_TABLE}}": "\n".join(rows), "{{ASSETS3D_QUALITY}}": q}


if __name__ == "__main__":
    tpl, outp, csvp = sys.argv[1:4]
    tok_json, contrast_md = sys.argv[4:6]
    wbs, summary, m, a = render()
    text = open(tpl).read().replace("{{WBS_SUMMARY}}", summary).replace("{{WBS}}", wbs)
    for k, v in render_tokens(tok_json, contrast_md).items():
        text = text.replace(k, v)
    here = os.path.dirname(os.path.abspath(__file__))
    for k, v in render_assets3d(os.path.normpath(os.path.join(here, "..", "..", "assets3d", "dist", "summary.json"))).items():
        text = text.replace(k, v)
    text = text.replace("{{MVP_PD}}", str(m)).replace("{{ALL_PD}}", str(a)).replace("{{N_TASKS}}", str(len(T)))
    import re as _re
    assert not _re.search(r"\{\{[A-Z_]+\}\}", text), "unreplaced placeholder"
    open(outp, "w").write(text)
    with open(csvp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "phase", "title", "roles", "estimate_pd", "mvp", "depends_on", "done_when"])
        for tid, title, roles, days, mvp, deps, done in T:
            w.writerow([tid, tid.split("-")[0], title, roles, days, "yes" if mvp else "no", ";".join(deps), done])
    print(f"tasks={len(T)} mvp_pd={m} total_pd={a}")
