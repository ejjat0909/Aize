#!/usr/bin/env python3
"""Generate docs/03-roadmap.md from docs/backlog.csv plus a status map.

The backlog (100 tasks, 653 pd) comes from docs/02-aize-build-plan.md. This script
adds what is actually built as of the current release, so the plan and reality
cannot drift apart: change STATUS here when a task lands, then re-run.

    python3 scripts/generate_roadmap.py
"""
import csv
import datetime
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "backlog.csv"
OUT = ROOT / "docs" / "03-roadmap.md"

# id -> (state, note). state: done | partial | todo
# A note is only needed for partial/todo work that needs explaining.
STATUS = {
    "P0-01": ("done", 'Decision record in `docs/adr/d-decisions.md` (D1 pilot region, D5 licence GPL-3.0, D7 minSdk 26, D4 no ads). Trademark clearance is the one item still open, and it needs the owner (D6).'),
    "P0-02": ("done", 'Gradle KTS + version catalog, `core/` and `backend/` Rust workspaces, `proto/` linted with buf, design pipeline, docs, CI.'),
    "P0-03": ("done", 'Gradle 9.8.2, AGP 9.4.1, Kotlin 2.4.21, compileSdk 37, Rust stable 1.99, buf 1.75, JDK 17. No NDK, so the UniFFI bridge (P4-06) waits; no Docker, so Valhalla runs from the prebuilt wheel.'),
    "P0-04": ("done", 'Four CI jobs: Android (token drift, no-Waze gate, unit tests, debug + R8 release build), Rust (fmt, clippy `-D warnings`, tests), proto (buf lint/build), security (CodeQL).'),
    "P0-05": ("done", ""),
    "P0-06": ("done", 'GPL-3.0 `LICENSE`, updated `NOTICE.md`, `docs/PRIVACY.md` skeleton, and `scripts/check_no_waze_assets.py` as a CI gate.'),
    "P0-07": ("partial", 'Valhalla 3.9.1 (735 tiles) and the 685k-place FTS5 index are built and running. Own Planetiler tiles are not: `server/dev/docker-compose.yml` is written but has never been run (no Docker here).'),
    "P0-08": ("done", ""),
    "P0-09": ("done", '`:benchmark` Macrobenchmark module, JankStats in debug, Perfetto script, baseline-profile generator. First numbers: 3.54 s cold TTID on the software-rendered emulator — `docs/verification/p0-perf.md`.'),
    "P0-10": ("partial", 'Opt-in `Telemetry` (no-op unless enabled, logcat sink only, nothing leaves the device) and `FeatureFlags` with defaults on parse failure. No remote fetch and no crash reporter: ADR-19 leaves the vendor open.'),
    "P0-11": ("partial", 'Release signing from environment variables only, R8 release build proven (47 MB), CodeQL in CI. No dependency verification metadata and no secrets scan yet.'),
    "P1-01": ("partial", "Light and dark themes generated from tokens. Typography is still default Roboto (no Figtree subset); spacing/shape roles only partly applied."),
    "P1-02": ("partial", "Launcher, close and search icons only — about 5 of ~60."),
    "P1-03": ("todo", "Everything is stock Material 3 so far."),
    "P1-04": ("partial", "Instruction banner with next and next-next maneuver. No lane strip, ETA bar, speed bubble, report button, arrival card."),
    "P1-05": ("todo", ""),
    "P1-06": ("todo", ""),
    "P1-07": ("todo", ""),
    "P1-08": ("partial", "Single Activity, one screen, no navigation graph, no onboarding, permission rationale or consent flow."),
    "P1-09": ("todo", ""),
    "P1-10": ("todo", ""),
    "P1-11": ("todo", ""),
    "P1-12": ("done", ""),
    "P2-01": ("partial", "MapLibre 13.7.1 lives in `:app`; no separate `:map` module, no frame-stats hook."),
    "P2-02": ("done", ""),
    "P2-03": ("partial", "`scripts/fetch-dev-tiles.sh` pulls a KL extract. No Planetiler profile, no object storage or CDN, no weekly refresh."),
    "P2-04": ("partial", "`MapController` does follow/overview/center-on-me and the camera pitch presets. No speed-adaptive zoom, no HUD inset API."),
    "P2-05": ("partial", "Nearest pitch bucket and nearest of 24 yaws from the Blender sheets. No blending, no dead-reckoned interpolation, no accuracy circle."),
    "P2-06": ("partial", "Casing, fill and the greyed passed part. No traffic segments, alternatives, tap-to-select or ETA labels."),
    "P2-07": ("partial", "Destination pin only; the other eight billboard pins are rendered but unused."),
    "P2-08": ("partial", "Raw `LocationManager` fixes with a permission gate. No fused provider, rotation vectors, mock flagging or adaptive rates."),
    "P2-09": ("todo", "Navigation currently stops if the Activity dies."),
    "P2-10": ("todo", ""),
    "P2-11": ("todo", "Dark mode follows the system setting only."),
    "P2-12": ("todo", ""),
    "P2-13": ("todo", "Hatch and van are not rendered; no skin picker."),
    "P3-01": ("partial", "Debounced search with a result list. No category chips, recents, favourites or along-route search."),
    "P3-02": ("partial", "Deliberate deviation: SQLite FTS5 over the OSM extract instead of a Photon deployment, because Photon needs Java and a large index. No reverse geocoding, cache or rate limits."),
    "P3-03": ("partial", "`kind` comes from OSM tags and drives ranking. No opening hours, no category taxonomy beyond the tag pair."),
    "P3-04": ("todo", "Tapping a result starts routing immediately; there is no place card."),
    "P3-05": ("partial", "`costing=auto`, no alternatives, no avoid options, lanes/speed limits/tolls not mapped."),
    "P3-06": ("todo", ""),
    "P3-07": ("todo", "Route decoding is Kotlin; the Rust port is blocked on a toolchain."),
    "P3-08": ("todo", ""),
    "P3-09": ("todo", ""),
    "P3-10": ("todo", ""),
    "P3-11": ("partial", "Kilometres and 24-hour clock only."),
    "P4-01": ("todo", "No map matching: the app projects onto the route it already has."),
    "P4-02": ("partial", "Windowed projection gives progress, distance to the next maneuver and the passed part. No hysteresis, tunnel dead reckoning, remaining time."),
    "P4-03": ("partial", "40 m threshold, 3 strikes, 15 s cooldown, armed only after the first on-route fix. No accuracy awareness, heading mismatch, rejoin logic or better-route suggestion."),
    "P4-04": ("partial", "Maneuver timeline with next and next-next instructions and arrival within 30 m. No speed-adaptive triggers, lane guidance, roundabout exits or camera zones."),
    "P4-05": ("partial", "Valhalla's time is shown as-is. No smoothing or arrival clock."),
    "P4-06": ("todo", "Blocked: no Rust toolchain on the build VM."),
    "P4-07": ("partial", "Banner and follow camera. No lane view, speedometer, limit sign or traffic bar."),
    "P4-08": ("todo", "No voice at all."),
    "P4-09": ("todo", ""),
    "P4-10": ("todo", ""),
    "P4-11": ("todo", "Verification so far is emulator `geo fix`; there is no GPX/NMEA replay harness."),
    "P4-12": ("todo", ""),
    "P4-13": ("todo", ""),
    "P4-14": ("todo", ""),
}

PHASE_GOALS = {
    "P0": ("Foundations & decisions", "A walking skeleton: purple map, a puck, a route drawn."),
    "P1": ("Design system & app shell", "Every screen is built from the Aize component library; nothing is stock Material."),
    "P2": ("Map & location", "The map looks and moves like the design spec; the puck is smooth at 60 fps."),
    "P3": ("Search, places & routing", "Type a destination, see a place card, pick among routes, start."),
    "P4": ("Navigation engine & voice", "It guides you by voice and recovers when you leave the route."),
    "P5": ("Live traffic & community", "Reports, alerts and traffic-aware routing from real probes."),
    "P6": ("Planning, sharing & accounts", "Plan a drive, share an ETA, keep history."),
    "P7": ("Android Auto", "The same guidance on the car screen."),
    "P8": ("Polish, accessibility & performance", "Holds up on real devices, in every language, at every font size."),
    "P9": ("Hardening & launch", "In the Play Store, with the evidence to defend it."),
}

# Milestones: what a person can actually do at each point.
MILESTONES = [
    ("M1", "Drive with it", ["P4-04", "P4-05", "P4-07", "P4-08", "P4-11", "P4-12", "P2-09", "P2-11"],
     "A phone in a car bracket guides a real drive: voice prompts, speed-adaptive turn triggers, "
     "lane guidance, ETA that settles, and navigation that survives the screen turning off."),
    ("M2", "Choose where to go", ["P3-01", "P3-04", "P3-05", "P3-06", "P3-08", "P3-11", "P2-07"],
     "Search with categories and recents, a place card with actions, up to three routes with tolls "
     "and a turn list, favourites, and all nine map pins in use."),
    ("M3", "Look right", ["P1-02", "P1-03", "P1-04", "P1-05", "P1-07", "P1-08", "P1-10", "P2-05", "P2-06"],
     "The design spec is realised: the component library, the HUD pieces, motion tokens, a puck "
     "that blends instead of popping, and accessibility built in rather than bolted on."),
    ("M4", "Ship a beta", ["P0-09", "P0-11", "P8-06", "P8-07", "P8-08", "P9-03", "P9-05"],
     "Signed AAB, measured performance budgets, Play internal testing with real testers, "
     "crash-free above 99.5%."),
    ("M5", "Community", ["P5-03", "P5-04", "P5-05", "P5-06", "P5-12", "P5-07", "P5-08"],
     "Report a hazard in three taps, see alerts on your route, traffic-coloured roads, and "
     "probes that feed the traffic model."),
    ("M5b", "Full traffic", ["P5-01", "P5-02", "P5-09", "P5-11", "P4-01", "P4-03"],
     "Real probe ingest and aggregation, moderation, and map matching that fixes the remaining "
     "false-reroute cases."),
    ("M6", "Ship it", ["P8-01", "P8-02", "P8-03", "P8-04", "P8-05", "P9-01", "P9-02", "P9-03", "P9-04", "P9-05", "P9-06", "P9-07"],
     "Localised, audited, measured over 50 real drives, and published."),
    ("Later", "Beyond the MVP", ["P6-01", "P6-02", "P6-03", "P7-01", "P3-10", "P6-06", "P2-12", "P4-09", "P4-10"],
     "Accounts, planned drives, ETA sharing, Android Auto, offline regions, original voice packs."),
]

PHASE_NOTES = {
    "P5": "The MVP part is small: report a hazard (P5-03, P5-05), see alerts on your route (P5-04, P5-06), "
          "and the taxonomy behind both (P5-12). The expensive half is the traffic engine — probe upload, "
          "map matching to edges, aggregation with k-anonymity, live-traffic tiles (P5-01, P5-02) — which "
          "needs a real backend and PostGIS, and only pays off with enough drivers. Do the MVP half first "
          "and treat traffic as a separate project.",
    "P6": "Optional for an MVP. Guest-only keeps the privacy work small; accounts only earn their place if "
          "you want ETA sharing or planned drives.",
    "P7": "Cannot start until navigation runs headless (P4-12). Also needs a Desktop Head Unit test plan and "
          "a Play review for the navigation category, so budget review time, not just build time.",
    "P8": "Every task here needs a real device and the performance budgets from P0-09 to measure against. "
          "Running this before P0-09 is guesswork.",
    "P9": "The Play Console work (data-safety form, foreground-service and background-location declarations "
          "with video) is tedious and unforgiving; start it at M4, not at the end.",
}

IMMEDIATE = [
    ("Turn-by-turn from real GPS", "P4-04, P4-05",
     "Today the banner advances only as far as the next maneuver and the distance is a straight-line "
     "projection. Make it a proper guidance engine: speed-adaptive prepare/approach/now triggers, "
     "distance to the maneuver point rather than to the segment, remaining time and distance, and an "
     "arrival clock that does not jump around."),
    ("Voice", "P4-08",
     "Android `TextToSpeech` first, with a scheduler that de-duplicates prompts and respects audio "
     "focus and ducking. The 51-prompt catalogue in `docs/02-aize-build-plan.md` §8.2 is the contract; "
     "studio recordings come later."),
    ("Navigation that survives the screen", "P2-09, P4-12",
     "Move the navigation loop into a foreground service with the `location` type, an ETA notification, "
     "and Android 14 compliance. Without it the app stops guiding when the screen turns off, which is "
     "the single biggest thing between this and a usable driving app."),
    ("A test harness you can trust", "P4-11",
     "GPX/NMEA replay with a speed multiplier and scripted scenarios (missed turn, tunnel, GPS jump, "
     "U-turn). Right now every behaviour is checked by hand on an emulator, which does not scale and "
     "cannot catch regressions."),
    ("Place card and route choice", "P3-04, P3-05, P3-06",
     "Tapping a search result should open a card (distance, ETA, Go/Save/Share), and Go should offer "
     "up to three routes with tolls and a turn list before starting."),
    ("Release signing and a real beta", "P0-11, P9-03, P9-05",
     "A signed AAB, the Play data-safety form, the foreground-service and background-location "
     "declarations, and an internal testing track."),
]

DECISIONS = [
    ("Where the server lives, for good", "Decided: a Small VM with an always-on link, about $5 per 30 days. "
     "Revisit only if you want a real host with a domain and TLS."),
    ("Do you want the Rust core?", "The plan has `aize-core` in Rust behind UniFFI for map matching and the "
     "guidance engine. It needs a Rust toolchain and NDK on the build machine. Kotlin alone can carry M1 and "
     "M2; Rust matters from P4-01 and P5-02 onwards, where the maths gets heavy."),
    ("Offline or online only?", "Offline regions (P2-12) change the data pipeline, the app size and the store "
     "listing. Worth deciding before the tile pipeline is hardened in P2-03."),
    ("Accounts at all?", "P6 is entirely optional for an MVP. Guest-only keeps the privacy story simple and "
     "removes the DPIA work in P9-02, but also removes ETA sharing and sync."),
    ("How far do you want to go on voice?", "System TTS is a day of work; the recorded Aize voice set is a "
     "studio booking plus 51 prompts in two languages."),
]

BLOCKERS = [
    ("No Docker", "Planetiler and Photon have no images to run here. Routing and search were built without "
     "them; own tiles (P2-03) and a Photon deployment (P3-02) still need either Docker or a native build."),
    ("No Rust, no NDK, no JDK 21", "P4-06, P3-07 and all of `aize-core` are blocked. The build VM has JDK 17, "
     "which the project targets, so this costs nothing today."),
    ("One emulator, software rendering", "Every performance number so far is from swiftshader. P0-09 and the "
     "P8 passes need a real device."),
    ("Disk", "The build VM runs at about 86% full with the emulator images, the Android SDK, the routing tiles "
     "and the search index on it. A clean build needs roughly 2 GB free."),
]


def main():
    rows = list(csv.DictReader(open(BACKLOG)))
    for r in rows:
        # Everything from P5 on is untouched, so a new task there is todo by default.
        # Earlier phases must be listed explicitly, or a status could silently drift.
        if r["id"] not in STATUS and r["phase"] < "P5":
            sys.exit(f"no status for {r['id']} — add it to STATUS in {__file__}")
    state = {r["id"]: STATUS.get(r["id"], ("todo", ""))[0] for r in rows}
    left = {r["id"]: float(r["estimate_pd"]) * {"done": 0, "partial": 0.5, "todo": 1}[state[r["id"]]] for r in rows}
    phases = []
    for r in rows:
        if r["phase"] not in phases:
            phases.append(r["phase"])

    out = []
    a = out.append
    today = datetime.date.today().isoformat()
    a("# 03 · Roadmap to done")
    a("")
    a(f"> Generated from `docs/backlog.csv` by `scripts/generate_roadmap.py` on {today}. "
      "The backlog is the work breakdown in `docs/02-aize-build-plan.md`; this file adds what is "
      "actually built, what is next, and in what order. Re-run the script when a task lands instead "
      "of editing this by hand.")
    a("")
    a("## Where the app is today")
    a("")
    a("Version 0.3.0-p1. A debug APK installs and runs on a real phone: purple MapLibre basemap from "
      "bundled PMTiles, Blender-rendered puck and destination pin, live Valhalla routing from a server "
      "with a permanent address, place search over 685k named places, off-route detection with reroute, "
      "and a turn-by-turn banner. 20 JVM unit tests pass.")
    a("")
    a("What it is not yet: it does not speak, it stops guiding when the screen turns off, it has no "
      "place card or route choice, no reports or traffic, no settings, and the release build is unsigned.")
    a("")
    a("| Phase | Name | Tasks | Planned | Left (est.) | MVP |")
    a("|---|---|---|---|---|---|")
    for p in phases:
        pr = [r for r in rows if r["phase"] == p]
        pd = sum(float(r["estimate_pd"]) for r in pr)
        lft = sum(left[r["id"]] for r in pr)
        mv = sum(float(r["estimate_pd"]) for r in pr if r["mvp"] == "yes")
        name = PHASE_GOALS.get(p, (p, ""))[0]
        a(f"| {p} | {name} | {len(pr)} | {pd:g} pd | {lft:g} pd | {'yes' if mv else 'no'} |")
    tot = sum(float(r["estimate_pd"]) for r in rows)
    tot_left = sum(left.values())
    a(f"| **all** | | **{len(rows)}** | **{tot:g} pd** | **{tot_left:g} pd** | 337 pd MVP |")
    a("")
    mvp_left = sum(left[r["id"]] for r in rows if r["mvp"] == "yes")
    a("`pd` is person-days as planned in the WBS. \"Left\" counts finished tasks at zero and half-done "
      "ones at half, so treat it as an estimate, not a promise. On that basis the MVP has "
      f"**{mvp_left:g} pd** left of the 337 pd planned for it, and the whole plan has {tot_left:g} pd "
      "left of 653.")
    a("")
    a("## The order to do it in")
    a("")
    a("Milestones are the order that gets a usable product soonest, not the phase numbering. Each one "
      "ends with something you can hand to a person.")
    a("")
    a("| Milestone | What you can do at the end | Tasks |")
    a("|---|---|---|")
    for mid, title, tasks, desc in MILESTONES:
        a(f"| **{mid} · {title}** | {desc} | {', '.join(tasks)} |")
    a("")
    a("## Start here: the next six pieces of work")
    a("")
    for i, (title, refs, why) in enumerate(IMMEDIATE, 1):
        a(f"### {i}. {title}  ·  {refs}")
        a("")
        a(why)
        a("")
    a("## Phase by phase")
    a("")
    for p in phases:
        pr = [r for r in rows if r["phase"] == p]
        name, goal = PHASE_GOALS.get(p, (p, ""))
        pd = sum(float(r["estimate_pd"]) for r in pr)
        lft = sum(left[r["id"]] for r in pr)
        done = sum(1 for r in pr if state[r["id"]] == "done")
        part = sum(1 for r in pr if state[r["id"]] == "partial")
        a(f"### {p} · {name}")
        a("")
        a(f"*Exit criterion:* {goal}")
        a("")
        a(f"{len(pr)} tasks, {pd:g} pd planned, {lft:g} pd left. {done} done, {part} part-done.")
        a("")
        a("| Task | What | pd | MVP | Status |")
        a("|---|---|---|---|---|")
        icon = {"done": "done", "partial": "part", "todo": "—"}
        for r in pr:
            st = state[r["id"]]
            title = r["title"].replace("|", "\\|")  # a pipe in a title would split the cell
            a(f"| {r['id']} | {title} | {r['estimate_pd']} | {r['mvp']} | {icon[st]} |")
        a("")
        if p in PHASE_NOTES:
            a(PHASE_NOTES[p])
            a("")
        notes = [(r["id"], STATUS.get(r["id"], ("", ""))[1]) for r in pr if STATUS.get(r["id"], ("", ""))[1]]
        if notes:
            for tid, note in notes:
                a(f"- **{tid}** — {note}")
            a("")
    a("## Infrastructure as it stands")
    a("")
    a("| What | Where | Notes |")
    a("|---|---|---|")
    a("| Routing + search | Small VM, permanent link | Valhalla 3.9.1 with the full Malaysia/Singapore/Brunei "
      "graph (735 tiles, 652 MB) and the 88 MB FTS5 search index, three systemd units behind one port |")
    a("| Build machine | XL VM | Android SDK 37, Gradle 9.8.2, Blender 4.5.9, emulator AVD `api34` |")
    a("| Source | `github.com/ejjat0909/Aize` | `main`, debug APKs shared as assets rather than committed |")
    a("")
    a("## Decisions this plan is waiting on")
    a("")
    for q, why in DECISIONS:
        a(f"- **{q}** — {why}")
    a("")
    a("## Blockers on this machine")
    a("")
    for q, why in BLOCKERS:
        a(f"- **{q}** — {why}")
    a("")
    a("## Definition of done for the whole app")
    a("")
    a("1. A signed release AAB on an internal, then open, Play track.")
    a("2. A drive of at least 30 minutes on a real phone with voice, lane guidance and no false reroutes.")
    a("3. Crash-free sessions above 99.5% over the beta.")
    a("4. Frame time inside budget on a mid-range device (P0-09 budgets, ratcheted).")
    a("5. Search and routing that answer in under a second for the pilot region, on the permanent server.")
    a("6. Privacy: no location leaves the device except to the user's own server; DPIA and data-safety form done.")
    a("7. Every generated artefact reproducible from the repo: design tokens, 3D sprites, tiles, index.")
    a("")

    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} lines, {tot_left:g} pd left of {tot:g}")


if __name__ == "__main__":
    main()
