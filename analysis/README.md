# analysis — static reverse-engineering pipeline

Everything here is **static**: the APK is read as a ZIP/ELF/DEX/PCK file and never installed or executed. Outputs are names, counts, sizes and numeric design parameters — no media, no decompiled source.

## Requirements

| Tool | Needed for | Notes |
|---|---|---|
| `python3` ≥ 3.10 | all scanners | stdlib only (`render_preview.py` in `design/` needs Pillow) |
| `aapt2` (Android SDK build-tools) | resource table dump | set `AAPT2=/…/build-tools/34.0.0/aapt2` |
| `openssl` | signing certificate subject/validity | optional |
| `rea` CLI (`npm i -g rea-agents@6.7.0`) | whole-APK inventory evidence, JADX-backed class/method inspection | optional; see below |
| `jadx-headless-mcp-0.7.1-all.jar` + Java 17+ | `inspect-android-class/-method` | **supplied by you** (`REA_JADX_MCP_JAR`); REA does not install it |

## Run

```bash
AAPT2=/path/to/aapt2 bash analysis/tools/run_all.sh /path/to/waze.apk analysis/data --no-rea
```

Re-running on the analysed APK (`com.waze` 5.22.90.123, SHA-256 `a45040ac…c08c80`) reproduces **all 16 data files byte-for-byte** (apart from `scan_seconds` timing fields); this was verified.

| Script | Output (`analysis/data/`) |
|---|---|
| `apk_inventory.py` | `inventory.json`, `apk_files.csv` — buckets, sizes, duplicates, case-collisions |
| `resources_parse.py` (+`axml.py`, `framework_ids.json`) | `resources_summary.json`, `design_tokens.json`, `motion.json`, `layouts.json`, `resource_files.csv` |
| `manifest_parse.py` | `manifest.json` (secrets-looking meta-data values redacted) |
| `dex_scan.py` | `dex_summary.json` — classes, packages, libraries, JNI classes, URLs/hosts, credential-shape *counts* |
| `elf_scan.py` | `libwaze_summary.json`, `libogg_opus_summary.json` — sections, imports/exports, banners, source tree, RTTI, proto names |
| `pck_scan.py` | `pck_summary.json`, `pck_files.csv` — Godot 4 pack directory |
| `features_scan.py`, `assets_scan.py` | `features.json`, `assets.json` — settings ids, key families, TTS keys, skins, sounds, search config |
| `signing_scan.py` | `signing.json` — APK Signature Scheme v2/v3, certificate fingerprint (personal CN redacted) |
| `dex_class_detail.py` | *local use only*: per-class call skeletons from bytecode (its output is **not** committed) |
| `render_structure_report.py` | `docs/01-waze-apk-structure-report.md` from the data above |

## REA (Reverse Engineer Anything) and the skill

* REA: <https://github.com/morluto/rea> — `rea-agents` 6.7.0 was used (`rea inspect-artifact`, `inspect-android-class`, `inspect-android-method`, `doctor`).
* The **skill** `reverse-engineer-anything` is instruction-only; it does not register the REA MCP server in an agent. Install notes and the static-analysis-only wrapper are in [`rea-skill/`](rea-skill/INSTALL.md).
* Evidence IDs of every REA call are in `data/rea_evidence_index.json` and quoted in the report's Appendix A.

### Memory: why JADX runs on single-dex slices

Loading the whole APK (60,430 classes in 10 DEX files) into JADX was **OOM-killed on a 1 GiB VM** (the kernel killed the `java` process; REA reported `cancelled`). REA's own docs note that the JVM heap is not a total-memory cap. The same tools work on a **single-dex slice** (≈ 23 s, ≈ 410 MB peak RSS):

```bash
python3 analysis/tools/make_dex_slice.py waze.apk classes6.dex tmp/mini-classes6.apk
REA_JADX_MCP_JAR=/path/to/jadx-headless-mcp-0.7.1-all.jar REA_JADX_HEAP_MIB=300 \
  rea inspect-android-method tmp/mini-classes6.apk com.waze.map.opengl.WazeRenderer l --format json
# or run the curated batch used for the report (class → dex mapping is specific to 5.22.90.123):
APK=waze.apk bash analysis/tools/rea_android_batch.sh
```

Cross-dex references stay unresolved in slice output. A full pass needs a larger machine (plan §10, RE-01).

## What the pipeline deliberately does not do

No installation, emulation, dynamic instrumentation, traffic capture, native disassembly or protobuf field reconstruction. No credential, key or token is written to any output (credential-shaped strings are only *counted*; there were none in the DEX or native strings). The decompiled text REA produced is kept out of the repository and summarised as pseudocode in the report.

## Reference data

`data_ref/voicepack_valid_filenames.txt` — the 43 prompt file names of the community voice-pack schema, copied as **facts** from `pipeeeeees/waze-voicepack-links` (`mp3_upload/valid_waze_filenames.txt`, GPL-3.0 repository; no code is reused). It is used to compare against the APK's built-in prompt sets.
