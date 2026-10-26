# NOTICE

## Originality
Aize is an original work. The 3D models in `assets3d/` (pointer, vehicle skins, map pins) were built procedurally from primitives; no mesh, texture or glyph was imported or traced. This repository must not contain any file taken from a Waze/Google APK or service: no code (decompiled or otherwise), images, icons, animations, sounds, voice recordings, fonts, string tables or map styles. Design *measurements* (radii, durations, easing curves, structure) observed in the analysis are recorded as numbers in `analysis/data/` and re-expressed as Aize design tokens.

## Trademarks
"Waze" (and related names and marks) belong to their owners. Aize is not affiliated with, endorsed by, or connected to Waze or Google. Aize's name, logo and mascot are its own; no Waze marks may be used in the product.

## Research scope
`analysis/` contains static-analysis tooling and derived structural data about one lawfully obtained build of a public Android application, produced for interoperability research and learning. It lists names, counts, sizes and numeric parameters only. It contains no credentials, no keys, and no instructions for calling Waze's private services. If a rights holder believes anything here should be removed, please open an issue.

## Third-party references (not redistributed here)
| Item | Licence | Use |
|---|---|---|
| REA — Reverse Engineer Anything (`morluto/rea`) | MIT | analysis tooling (invoked, not vendored); `analysis/rea-skill/rea_skill.py` is original |
| Community voice-pack archive (`pipeeeeees/waze-voicepack-links`) | GPL-3.0 | the 43 prompt **file names** are copied as facts into `analysis/data_ref/`; no code reused; no audio redistributed |
| Blender 4.5 LTS (`assets3d/blender/install_blender.sh` downloads it; not vendored) | GPL-3.0-or-later | headless renderer for the 3D assets. Per the Blender Foundation's FAQ the *output* belongs to its author; whether the `import bpy` scripts must be distributed under a GPL-compatible licence is to be settled together with the repository licence (plan decision D5) |
| DejaVu fonts | Bitstream Vera / public domain changes | captions in generated preview images only |
| OpenStreetMap data (via the Protomaps daily build, `scripts/fetch-dev-tiles.sh`) | ODbL | **used in the P0 APK**: bundled dev basemap tiles; "© OpenStreetMap contributors" is shown in the map's attribution control. Protomaps basemap schema/tiles: ODbL data, CC0 tooling |
| Valhalla (recorded `/route` response, `app/src/main/assets/route/`) | MIT engine; OSM-derived result (ODbL) | one fixture route, KL Sentral → KLCC, used by the demo drive; the app makes no network call to a router |
| Noto Sans (`app/src/main/assets/glyphs/`) | SIL OFL 1.1 | map label glyph PBFs (Regular, Medium, Italic; code points 0–511) |
| MapLibre Native Android 13.7.1 | BSD-2-Clause | **used in the P0 APK** (map rendering) |
| AndroidX / Jetpack Compose / Material 3, Kotlin, kotlinx.coroutines | Apache-2.0 | **used in the P0 APK** |
| Planetiler, Photon | Apache-2.0 | planned components (see plan §2.2) |
| Figtree, Roboto | SIL OFL 1.1 / Apache-2.0 | planned typefaces |

## Licence
No licence has been chosen for Aize yet; all rights are reserved by default until the owner adds one (plan decision D5).
