# Owner decisions (D1–D9)

The open questions from §0 of the build plan, with the answer the project is using. Changing one means editing this file in the same commit.

| # | Question | Decision | Decided |
|---|---|---|---|
| D1 | Pilot region | Malaysia–Singapore–Brunei routing and search; Klang Valley for the bundled basemap. English first, Malay later | in use since P0 |
| D2 | Team size and calendar | Not set. `docs/03-roadmap.md` is in person-days so it does not depend on this | open |
| D3 | MVP scope | As tabulated in §1 of the plan; the roadmap's "MVP" column follows it | accepted |
| D4 | Business model | None at launch: no ads, no subscription, no third-party tracking SDKs | accepted default |
| D5 | Repository licence | **GPL-3.0-or-later** (`LICENSE`) | owner, 2026-11-04 |
| D6 | Brand: logo, domain, store name | Working name "Aize", placeholder launcher icon. No domain, no trademark search yet | **open** (needs the owner) |
| D7 | minSdk | **26** (deviation from the plan's 29): wider device coverage while foreground-service rules are not yet in use. Revisit at P4-12 | decided |
| D8 | Paid routing API as fallback | No | accepted default |
| D9 | Large VM for the deeper APK pass | No. The plan does not depend on it | accepted default |

## What the licence means in practice

* GPL-3.0 covers the repo's own code, the Blender scripts (this settles the open question in `NOTICE.md`) and the generated assets.
* Everything the app depends on is GPL-3-compatible: Apache-2.0 (AndroidX, Kotlin, coroutines), BSD-2-Clause (MapLibre Native), MIT (Valhalla), SIL OFL (fonts), ODbL (OpenStreetMap data, kept separate as data, not code).
* The owner can still ship the app on Google Play as the sole copyright holder. Outside contributions need a contributor agreement (or they must be accepted under GPL-3.0 only) before the app is relicensed or dual-licensed; add a `CONTRIBUTING.md` before the first outside pull request.
