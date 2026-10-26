#!/usr/bin/env python3
"""Render docs/01-waze-apk-structure-report.md from the extracted JSON/CSV data (no APK access needed).

usage: render_structure_report.py DATA_DIR OUT_MD
DATA_DIR holds: manifest.json inventory.json signing.json dex_summary.json libwaze_summary.json libogg_opus_summary.json
pck_summary.json pck_files.csv features.json assets.json resources_summary.json design_tokens.json motion.json layouts.json
resource_files.csv rea_evidence_index.json
"""
import collections
import csv
import json
import os
import re
import sys

D = sys.argv[1]
OUT = sys.argv[2]


def J(n):
    return json.load(open(os.path.join(D, n)))


man, inv, sig, dex, lib, opus = J("manifest.json"), J("inventory.json"), J("signing.json"), J("dex_summary.json"), J("libwaze_summary.json"), J("libogg_opus_summary.json")
pck, feat, assets, ressum, tokens, motion, layouts = J("pck_summary.json"), J("features.json"), J("assets.json"), J("resources_summary.json"), J("design_tokens.json"), J("motion.json"), J("layouts.json")
rea = J("rea_evidence_index.json")
pck_rows = list(csv.DictReader(open(os.path.join(D, "pck_files.csv"))))
res_rows = list(csv.DictReader(open(os.path.join(D, "resource_files.csv"))))

L = []


def w(*lines):
    L.extend(lines)


def table(headers, rows, align=None):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join((":---:" if (align and align[i] == "c") else ("---:" if (align and align[i] == "r") else "---")) for i in range(len(headers))) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r) + " |")
    return out


def n(x):
    return f"{x:,}"


def mb(x, d=1):
    return f"{x / 1e6:,.{d}f} MB"


def short(c):
    return c.replace("com.waze.", "~.")


# ---------------------------------------------------------------------------------------------------------------------
tot = dex["totals"]
fp = dex["first_party"]
mdv = man["manifest"]
sdk = man["sdk"]
comp = man["components"]
der = man["derived"]
jni = dex["jni_classes"]
jni_native = sum(j["native"] for j in jni)
cert = sig["certificates"][0]
by_bucket = {b[0]: b for b in inv["by_bucket"]}

w("# 01 · Waze Android APK — reverse-engineering structure report",
  "",
  f"> **Target:** `com.waze` **{mdv['versionName']}** (versionCode {mdv['versionCode']}) · universal APK, {mb(inv['apk_bytes'])} · SHA-256 `{inv['sha256']}`  ",
  "> **Analysed:** 2026-10-22 · **Mode:** static analysis only — the APK was never installed or executed  ",
  "> **Companion document:** [`02-aize-build-plan.md`](02-aize-build-plan.md) (what to build from these findings)",
  "",
  "This report answers one question: **what is inside the Waze APK and how is it structured?** "
  "Every number below was produced by the scripts in [`analysis/tools`](../analysis/tools) and is stored as machine-readable data in [`analysis/data`](../analysis/data). "
  "Where REA (Reverse Engineer Anything) produced the evidence, its evidence IDs are quoted so each claim can be re-verified.",
  "",
  "**Evidence legend** — **O** = *observed* directly in the artifact · **D** = *derived* by counting/joining observations · **I** = *inferred* (interpretation; confidence stated).",
  "",
  "**What is deliberately *not* in this repository:** the APK, decompiled source, Waze images/sounds/fonts/animations, string translations, certificates' private data, or any credential. "
  "No credential-shaped string was found in the DEX string pools or the native library (`analysis/data/dex_summary.json → credential_shaped_string_counts` is empty); "
  "the signer certificate's personal common name is redacted.",
  "",
  "---",
  "",
  "## 0 · TL;DR — what Waze is made of",
  "")
w(*table(["#", "Finding", "Evidence", "Why it matters for Aize"], [
    [1, f"**A thin Kotlin/Java shell around a {mb(lib['bytes'],0)} C++ core.** `libwaze.so` holds routing/navigation logic, rendering, networking queues, storage and voice; the Java side reaches it through {len(jni)} classes that declare `native` methods ({jni_native} in total; most are `*NativeManager` facades).", "O/D", "Aize must put its hot paths (matching, progress, reroute, voice scheduling) in a native core, not in UI code."],
    [2, f"**Structured data crosses JNI as protobuf.** {n(sum(c for _, c in feat['jni_protos_by_domain']))} generated classes (messages, builders, Kotlin DSL wrappers) live in `com.waze.jni.protos`; a GPS fix is serialised to bytes before it reaches the core.", "O", "Few, coarse calls with typed payloads beat many small JNI calls."],
    [3, "**The map is drawn by native code on its own render thread** from a raw Android `Surface` (GLES 3 + EGL). Java forwards size/surface events and calls `nativeRender()`, which returns a boolean *frame drawn?* — suggesting frames are produced on demand (inferred; the caller was not decompiled).", "O/I (REA/JADX)", "Map pan/zoom never touches the UI thread; the same pattern is available with MapLibre Native."],
    [4, f"**A custom Godot 4 engine is embedded** (`Godot Engine v4.4.2.rc … waze.custom`) with a {mb(pck['bytes'])} pack `waze_map_scenes.pck` that contains the *map overlay scenes*: alert pins, speed cameras, user-location puck, route-line shaders, pulsing alert glow, speedometer.", "O", "These are the \"animations on the map\" Aize must reproduce — with original art and GPU layers instead of a game engine."],
    [5, f"**Map style is data, not code:** a Lua skin with **{len(assets['skins']['map_categories'])} layer categories** × {assets['skins']['zoom_blocks']} zoom overrides, day and night palettes.", "O", "Aize needs an equivalent zoom-aware style (MapLibre style JSON) in purple."],
    [6, f"**UI is hybrid.** {ressum['layout_count']} layout XMLs (Views) plus Jetpack Compose ({n(dex['libraries'][1][1])} library classes, {tot['compose_singletons']} composable singletons, {ressum['compose_view_layouts']} layouts hosting `ComposeView`). The main screen, ETA bar and control panel are Compose hosted in a Views root.", "O/D", "Aize can be 100 % Compose and skip the legacy view layer entirely."],
    [7, "**Heavy build-time optimisation:** native code built with Google's LLVM 21 using **PGO + BOLT + LTO + MLGO**; an ART **baseline profile** ships in `assets/dexopt/`; 79.6 % of first-party classes have ≤ 2-character (R8-minified) names.", "O", "Performance is a build-pipeline feature: Aize needs LTO/PGO, baseline + startup profiles, R8 full mode from day one."],
    [8, f"**Voice = recorded prompt sets + TTS + user-recorded packs.** Built-in English/Hebrew sets use exactly the file names of the community voice-pack schema (all {assets['sound_vs_community_voicepack_schema']['community_valid_names']} names match); {feat['tts_keys']['count']} TTS phrase keys; a custom-prompt recorder/uploader.", "O/D", "Aize's voice system should be prompt-ID based, TTS-backed and import-compatible with user-owned packs."],
    [9, f"**Android Auto is a first-class surface** (`WazeCarAppService`, ~{n(sum(c for _, c in feat['car_lib_subpackages']))} `car_lib` classes, Car App Library level 9).", "O", "Plan a Car App Library module early; it constrains the architecture (headless navigation core)."],
    [10, f"**Size:** {mb(inv['apk_bytes'])} universal APK — native libs {mb(by_bucket['native: lib/arm64-v8a'][3] + by_bucket['native: lib/armeabi-v7a'][3])} (zipped, two ABIs), DEX {mb(by_bucket['code: dex'][3])}, PNG resources {mb(by_bucket['res: png'][3])}, Godot pack {mb(by_bucket['assets: godot pck'][3])}.", "D", "Aize's budget: per-ABI AAB splits, vector icons, no embedded game engine → a fraction of this."],
], ["c", "l", "c", "l"]))
w("", "```mermaid", "flowchart TB",
  "  subgraph APP[\"Android process — Kotlin/Java, R8-minified (17,361 first-party classes)\"]",
  "    UI[\"UI: Compose + Views<br/>waze_main_activity · ETA bar · reports · settings\"]",
  "    NM[\"~100 JNI facade classes<br/>(mostly *NativeManager; protobuf payloads)\"]",
  "    CAR[\"Android Auto — car_lib<br/>(Car App Library)\"]",
  "    SYS[\"Platform adapters<br/>LocationManager+sensors · OkHttp · TTS/audio · WorkManager · FCM\"]",
  "  end",
  "  subgraph NAT[\"libwaze.so — C++ (PGO+BOLT+LTO), 73 MB\"]",
  "    CORE[\"core: waze/src + cpp_modules<br/>navigation · map_navigation · realtime_insights · userdb · tile_reader · map_labels · map_ads · waze_asks\"]",
  "    GFX[\"renderer: GLES3 canvas + Lua skin<br/>+ embedded Godot 4.4 (waze_map_scenes.pck)\"]",
  "    PB[\"2,701 .proto schemas<br/>(client_protos · event payloads · geo/maps)\"]",
  "  end",
  "  UI --> NM --> CORE --> GFX",
  "  SYS <--> NM",
  "  CAR --> NM",
  "  CORE -->|gRPC + queued HTTP| SRV[(Waze servers)]",
  "```", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 1 · Scope, method and tooling", "")
w(*table(["Tool", "Version / source", "Used for"], [
    ["**REA — Reverse Engineer Anything**", "`rea-agents` 6.7.0 (npm) · repo `morluto/rea` @ `933af60` · skill `reverse-engineer-anything` v44 installed into the agent's skills directory", "`inspect-artifact` (APK graph, hashes, limitations), `inspect-android-method`, `inspect-android-class` (JADX provider), `doctor`"],
    ["JADX headless MCP", "`jadx-headless-mcp` 0.7.1 (supplied jar), heap 300 MiB", "Decompilation of selected methods/classes (single-dex slices — see §17)"],
    ["Android `aapt2`", "build-tools 34.0.0", "`dump badging`, `dump xmltree` (manifest), `dump resources` (resource table)"],
    ["Aize analysis scripts", "[`analysis/tools/*.py`](../analysis/tools)", "AXML reader, resource/manifest/DEX/ELF/PCK/asset/feature scanners, APK signing block parser"],
], ["l", "l", "l"]))
w("",
  f"REA evidence IDs: whole-APK inventory `{rea['apk_inventory']['evidence_id']}` (inventory sub-evidence `{rea['apk_inventory']['inventory_evidence_id']}`, {n(rea['apk_inventory']['occurrences'])} occurrences, {n(rea['apk_inventory']['unique_nodes'])} unique SHA-256 nodes, 0 integrity contradictions).  ",
  "The REA skill is an *instruction* skill: it does not register the REA MCP server inside this harness, so the equivalent `rea` CLI commands were used (same tools, kebab-case names). A thin wrapper (`rea_skill.py`) exposes **static-analysis commands only**; commands that launch/instrument a target, touch a device or install packages are refused.",
  "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 2 · APK identity and provenance", "")
w(*table(["Property", "Value", "Ev."], [
    ["Package / launcher", "`com.waze` / `com.waze.FreeMapAppActivity` (\"FreeMap\" is Waze's original project name)", "O"],
    ["Version", f"{mdv['versionName']} · versionCode {mdv['versionCode']}", "O"],
    ["SDK levels", f"minSdk {sdk['min']} · targetSdk {sdk['target']} · compileSdk {mdv['compileSdkVersion']} (`{mdv['compileSdkVersionCodename']}` preview codename)", "O"],
    ["Application class", "`com.waze.mobile.WazeMobileApplication`", "O"],
    ["Application flags", "`largeHeap=true` · `hardwareAccelerated=true` · `usesCleartextTraffic=false` · `allowBackup=false` · `supportsRtl=false` · `requestLegacyExternalStorage=true`", "O"],
    ["ABIs", "`arm64-v8a`, `armeabi-v7a` (no x86)", "O"],
    ["Signing", f"{' + '.join(sig['schemes'])}; one signer, self-signed, `{cert['subject']}`, valid {cert['not_before']} → {cert['not_after']}; cert SHA-256 `{cert['sha256']}`", "O"],
    ["Build chain", f"NDK **{lib['android_ident']['ndk_version']}** (api {lib['android_ident']['api_level']}), Google `clang 21.0.0`, **+pgo +bolt +lto +mlgo**, linker `LLD google3-trunk` — built inside Google's monorepo", "O"],
    ["Bundle origin", "meta-data `com.android.dynamic.apk.fused.modules=base` and `com.android.vending.splits` → a *universal APK fused from an Android App Bundle* (bundletool)", "O/I"],
    ["Archive", f"{n(inv['entries'])} entries · {mb(inv['uncompressed_bytes'])} uncompressed → {mb(inv['compressed_bytes'])} zipped · {n(inv['stored_uncompressed_entries'])} entries stored uncompressed", "D"],
], ["l", "l", "c"]))
w("", "**Observed quirks worth knowing before you extract this APK:**",
  f"- Resource files use **shortened, case-sensitive names** (`res/A8b.xml`, `res/-OU.png`). {inv['case_insensitive_collisions']} pairs differ only by letter case (e.g. `res/-OU.png` vs `res/-Ou.png`), so extracting on Windows/macOS silently drops files. REA reports the same limitation (inventory evidence).",
  f"- {inv['duplicate_content_groups']} groups of byte-identical files (≈{mb(inv['duplicate_redundant_bytes'])} redundant) — mostly duplicate voice prompts (`StartDrive3.mp3` ≡ `StartDrive8.mp3`, `400.mp3` ≡ `400meters.mp3`).",
  "- ZIP inventory cannot see the APK Signing Block (outside the ZIP entries); it was parsed separately.", "")

w("### 2.1 Where the 131 MB goes", "")
w(*table(["Bucket", "Files", "Uncompressed", "Zipped", "Share of zipped"], [
    [b, n(f), mb(u), mb(c), f"{100 * c / inv['compressed_bytes']:.1f} %"] for b, f, u, c in inv["by_bucket"] if c > 90_000], ["l", "r", "r", "r", "r"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 3 · Archive layout", "")
w("```text",
  "waze-5.22.90.123.apk",
  "├── AndroidManifest.xml                 binary XML (decoded in §4)",
  f"├── classes.dex … classes10.dex          10 DEX files · {n(tot['classes'])} classes · {n(tot['methods'])} methods (§5)",
  f"├── lib/{{arm64-v8a,armeabi-v7a}}/        9 libraries each; libwaze.so = {mb(lib['bytes'])} (arm64) (§6)",
  f"├── resources.arsc                       {mb(by_bucket['resources.arsc (table)'][2])} · {n(ressum['distinct_resources'])} resources · 86 string locales (§9)",
  f"├── res/                                 {n(sum(1 for r in res_rows))} registered files, flat + shortened names (§9)",
  "├── assets/",
  "│   ├── res/godot/waze_map_scenes.pck    Godot 4.4 scenes: map overlays (§8)",
  "│   ├── res/skins/default/               Lua map skin + 1,173 PNG + 12 .obj 3-D models (§8)",
  "│   ├── res/sound/{common,eng,heb}/      142 mp3 prompts & earcons (§12)",
  "│   ├── res/lang.{eng,heb,chinese}       native-UI translation tables (key=value)",
  "│   ├── res/key_value_tts_strings.txt    314 TTS phrase keys · res/tts/voices_was_tts.csv",
  "│   ├── res/search_conf                  server-generated search config (providers, categories)",
  "│   ├── dexopt/baseline.prof(m)          ART baseline profile",
  "│   └── phenotype/*.binarypb             Google Phenotype (Play services) config",
  "├── schemas/com.waze.stats.storage.StatsDatabase/3.json     Room schema (§14)",
  "├── okhttp3/internal/publicsuffix/…      OkHttp public-suffix list",
  "├── META-INF/services/…                  protobuf, gRPC, kotlinx.coroutines service files",
  "├── WazeTtsPlayerNativeManagerJniMethods.h, WazeTtsStringsProviderNativeManagerJniMethods.h   generated JNI headers",
  "└── car-app-api.level                    `9` (Car App Library API level)",
  "```", "")
w("**`assets/` in detail** (group, files, uncompressed, zipped):", "")
w(*table(["Path", "Files", "Uncompressed", "Zipped"], [[p, n(f), mb(u, 2), mb(c, 2)] for p, f, u, c in assets["assets_tree"][:14]], ["l", "r", "r", "r"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 4 · AndroidManifest", "")
w(f"**Totals:** {comp and len(comp['activity'])} activities · {len(comp['service'])} services · {len(comp['receiver'])} receivers · {len(comp['provider'])} providers · {len(man['usesPermissions'])} `uses-permission` · {len(man['usesFeatures'])} `uses-feature` · {der['with_intent_filters']} components with intent filters · exported: {der['exported_true']['activity']} activities, {der['exported_true']['service']} services, {der['exported_true']['receiver']} receivers, {der['exported_true']['provider']} providers.", "")
w("### 4.1 Permissions (grouped; purposes are inferred from the component that needs them)", "")
groups = [
    ("Location & driving", r"LOCATION|CAR_INFO|NAVIGATION_TEMPLATES|ACCESS_SURFACE", "Fix, background tracking during navigation, foreground service (type `location`), Android Auto surface/template access."),
    ("Audio & voice", r"RECORD_AUDIO|MODIFY_AUDIO", "Voice commands / custom-prompt recorder; ducking and routing of guidance audio."),
    ("Camera", r"CAMERA", "Photo reports and place photos (CameraX is bundled)."),
    ("Contacts, calendar, phone", r"READ_CONTACTS|READ_CALENDAR|READ_PHONE_STATE|READ_PROFILE", "Friends/ETA sharing, planned drives from calendar events, call-state aware audio."),
    ("Bluetooth", r"BLUETOOTH", "Car audio and BLE beacon scanning (`BeaconsNativeManager`)."),
    ("Notifications & overlay", r"POST_NOTIFICATIONS|SYSTEM_ALERT_WINDOW|WAKE_LOCK|VIBRATE|BROADCAST_STICKY|RECEIVE_BOOT|FOREGROUND_SERVICE$", "Navigation notification, reminders, over-app alert pop-ups, keep-awake."),
    ("Network & downloads", r"INTERNET|ACCESS_NETWORK_STATE|DOWNLOAD_WITHOUT", "API traffic; map/voice downloads."),
    ("Account sync", r"SYNC", "Legacy sync-adapter permissions."),
    ("Ads & push", r"AD_ID|c2dm", "Advertising ID; FCM push."),
    ("Custom", r"com\.waze\.", "Signature-level guards for dynamically registered receivers."),
]
perm_rows, used = [], set()
for label, rx, why in groups:
    names = [p["name"] for p in man["usesPermissions"] if re.search(rx, p["name"]) and p["name"] not in used]
    used.update(names)
    def plabel(x):
        if x.endswith("c2dm.permission.RECEIVE"):
            return "c2dm.RECEIVE (FCM)"
        if x.endswith("gms.permission.AD_ID"):
            return "gms.AD_ID"
        x = x.replace("android.permission.", "").replace("com.google.android.", "")
        return x if "." not in x else ".".join(x.split(".")[-2:])
    perm_rows.append([label, len(names), ", ".join(f"`{plabel(x)}`" for x in names), why])
w(*table(["Group", "#", "Permissions", "Purpose (inferred)"], perm_rows, ["l", "r", "l", "l"]))
w("", f"**Features:** {', '.join(f'`{f['name'].replace('android.hardware.', '')}`' + ('' if f['required'] == 'true' else ' (optional)') for f in man['usesFeatures'])}.  ",
  f"**`queries`:** packages `{'`, `'.join(man['queries']['packages'])}`; intents for TTS service, speech recogniser, image capture/crop, share-text, `com.waze.sdk.audio.ACTION_INIT` (Waze Audio Kit), window-extensions engagement mode.  ",
  "**Application meta-data:** Car App minimum API level **5** (`androidx.car.app.minCarApiLevel`), Google Mobile Ads application id (value redacted), Wallet API enabled, Crashlytics collection **disabled by default**, Firebase Performance logcat off.", "")

w("### 4.2 Activities (first-party) grouped by product area", "")
act = [c for c in comp["activity"] if (c["name"] or "").startswith("com.waze")]
area = [
    ("Launch & main", r"FreeMapAppActivity|\.MainActivity|WazeServiceHostActivity|UidFragmentActivity"),
    ("Search & destination", r"search|Autocomplete|LocationPreview|HistoryActivity|favorites|AddHomeWork"),
    ("Navigation & planning", r"trip_overview|planned_drive|ParkingUpdate|ClosureMap|ShareHelp|ViewShareDrive|CalendarApproved"),
    ("Reports & community", r"reports\.|rtalerts|RtAlerts|ifs\.|SosProviders|inbox|GasPrice|NearbyGas|EditPlace|AddPlace"),
    ("Settings & voice", r"settings\.|SimpleListMenu|CustomVoices|CustomPrompts|moods|mywaze|profile\."),
    ("Onboarding, permissions, web", r"install\.|RequestPermission|LocationPermission|RequestAlwaysLocation|InternalWebBrowser|SimpleWebActivity|ForgotPassword|SpeechRecognizerActivity|FeedbackActivity"),
    ("Debug", r"DebugConfig|PreviewActivity"),
]
rows, seen = [], set()
for label, rx in area:
    names = [c["name"] for c in act if re.search(rx, c["name"]) and c["name"] not in seen]
    seen.update(names)
    rows.append([label, len(names), ", ".join(f"`{short(x)}`" for x in names)])
rest = [c["name"] for c in act if c["name"] not in seen]
if rest:
    rows.append(["Other", len(rest), ", ".join(f"`{short(x)}`" for x in rest)])
w(*table(["Area", "#", "Activities"], rows, ["l", "r", "l"]))
w("", f"Launch modes: `MainActivity` and `LocationPermissionActivity` = **singleTask**, `SettingsMainActivity` = singleTop; Spotify's `LoginActivity` = singleInstance. **No activity pins `screenOrientation`.** `FreeMapAppActivity` is the only launcher and uses `Theme.Splash.Actual` (Android 12 SplashScreen API, V27/V29/V33 variants). Library activities: Play Core, Google sign-in/Credential Manager hidden activities, Car App permission activity, `androidx.compose.ui.tooling.PreviewActivity` (**exported, shipped in release**).", "")

w("### 4.3 Services, receivers, providers", "")
def comp_rows(lst):
    return [[f"`{short(c['name'])}`", c.get("exported", "—"), c.get("foregroundServiceType", ""), c.get("permission", "").replace("com.waze.", "~.")] for c in lst]
w(*table(["Service", "exported", "fg-type", "permission"], comp_rows(comp["service"]), ["l", "c", "c", "l"]))
w("", f"Receivers ({len(comp['receiver'])}): " + ", ".join(f"`{short(c['name'])}`" for c in comp["receiver"]) + ".  ",
  f"Providers ({len(comp['provider'])}): " + ", ".join(f"`{short(c['name'])}`" + (f" (`{c['authorities'].replace('${applicationId}', 'com.waze')}`)" if c.get('authorities') else '') for c in comp["provider"]) + ".", "")

w("### 4.4 Deep links and intent surface (public entry points)", "")
rows = []
n_plain = sum(1 for dl in der["deep_links"] if not (dl["schemes"] or dl["hosts"] or dl["paths"]))
for dl in der["deep_links"]:
    if not (dl["schemes"] or dl["hosts"] or dl["paths"]):
        continue
    rows.append([f"`{short(dl['component'])}`", ", ".join(f"`{s}`" for s in dl["schemes"]) or "—", ", ".join(f"`{h}`" for h in dl["hosts"]) or "—", ", ".join(f"`{p}`" for p in dl["paths"][:3]) or "—", "yes" if dl["autoVerify"] else ""])
w(*table(["Component", "Schemes", "Hosts", "Paths", "autoVerify"], rows, ["l", "l", "l", "l", "c"]))
w("", f"({n_plain} further `VIEW` filters carry only MIME types / non-URL data and are omitted.) The same set is registered on both `FreeMapAppActivity` (phone) and `WazeCarAppService` (car). Verified App Links: `waze.com`, `*.waze.com`, `beta.waze.com`, `*.gcp.wazestg.com` → `/ul*` (the documented **`waze.com/ul`** deep-link format). Waze also claims `geo:`, `google.navigation:`, `google.maps` and `maps.google.com/maps` links — standard behaviour for a navigation app.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 5 · Code structure (DEX)", "")
w(*table(["DEX", "Size", "Classes", "Methods", "Strings", "Fields"], [[d["dex"], mb(d["bytes"], 1), n(d["classes"]), n(d["methods"]), n(d["strings"]), n(d["fields"])] for d in dex["dex_files"]] + [["**Total**", mb(sum(d["bytes"] for d in dex["dex_files"])), f"**{n(tot['classes'])}**", f"**{n(tot['methods'])}**", n(sum(d['strings'] for d in dex['dex_files'])), n(tot['fields'])]], ["l", "r", "r", "r", "r", "r"]))
w("", f"Interfaces {n(tot['interfaces'])} · enums {n(tot['enums'])} · annotations {n(tot['annotations'])} · Kotlin markers (`*Kt`, `$Companion`, `$WhenMappings`) {n(tot['kotlin_markers'])} · D8 synthetic lambdas {n(tot['synthetic_lambdas'])} · API-modelling/backport stubs {n(tot['desugar_backports'])}. Seven of the ten DEX files hold 62–65.5 K method ids (the format limit is 65,536) — the signature of an automatic multidex split.", "",
  f"**Minification (D):** {n(fp['short_name_classes'])} of {n(fp['classes'])} first-party classes ({100 * fp['short_name_classes'] / fp['classes']:.1f} %) have ≤ 2-character names, and library code is renamed too (`h.*` ≈ Kotlin stdlib, `org.a.d.*` ≈ DI container, `kotlinx.b.*`). Library prefixes below are therefore a **lower bound**; JNI-bound classes and feature packages keep readable names because the native library looks them up by name.", "")

w("### 5.1 Library census (by original package prefix)", "")
w(*table(["Library / area", "Classes", "Methods"], [[l[0], n(l[1]), n(l[2])] for l in dex["libraries"]], ["l", "r", "r"]))
w("", "Present but renamed (inferred, **I**, medium confidence): Kotlin stdlib/coroutines internals, protobuf-lite runtime (`META-INF/services/com.google.protobuf.GeneratedExtensionRegistryLoader` is shipped), grpc-java (`META-INF/services/io.grpc.*` shipped; 13 un-renamed `AppIntegrationServiceGrpc*` classes come from the Google Assistant integration), Jackson (`com.fasterxml.*`, 1,051 classes) and a Koin-shaped DI container (the `Application.onCreate` loads a module array and resolves via `Scope.get(KClass, Qualifier, Function0)`). **Not found:** Retrofit, Gson, Hilt/Dagger, Coil, Picasso.", "")

w("### 5.2 First-party package map (`com.waze.*`)", "")
DOM = [
    ("Map rendering & canvases", r"^com\.waze\.(map|canvas|main_canvas|generic_canvas|gfx)(\.|$)"),
    ("Navigation, routing, trip overview", r"^com\.waze\.(navigate|modules\.navigation|app_nav|trip_overview|tripoverview|planned_drive|resume_drive|nav_connect|reroute)(\.|$)"),
    ("Search, places, favorites", r"^com\.waze\.(search|places|favorites|ifs|edit_place|parking|venue)(\.|$)"),
    ("Reports, alerts, community", r"^com\.waze\.(reports|reports_v2|rtalerts|alerters|asks|insights|insights_infra|beacons)(\.|$)"),
    ("Voice, audio, assistants", r"^com\.waze\.(sound|google_assistant|copilot|audio|speech|tts)(\.|$)"),
    ("Android Auto (Car App Library)", r"^com\.waze\.car_lib(\.|$)"),
    ("Settings, config, profile", r"^com\.waze\.(settings|config|moods|mywaze|profile)(\.|$)"),
    ("Account, onboarding, consent", r"^com\.waze\.(authentication|install|auth|onboarding)(\.|$)"),
    ("Social & sharing", r"^com\.waze\.(sharedrive|share|inbox|social)(\.|$)"),
    ("Network, location, telemetry", r"^com\.waze\.(network|location|stats|crash|analytics)(\.|$)"),
    ("JNI protobuf classes", r"^com\.waze\.jni(\.|$)"),
    ("UI kit (design system, views, popups, main screen)", r"^com\.waze\.(ui|uid|view|sharedui|design_components|main_screen)(\.|$)"),
    ("SDK & infrastructure", r"^com\.waze\.(sdk|shared_infra|modules|native_managers)(\.|$)"),
]
dom = collections.OrderedDict((d[0], [0, 0, 0]) for d in DOM)
dom["Other: R8-renamed packages and top-level `com.waze.*` classes"] = [0, 0, 0]
for pkg, c, m, nat in fp["packages"]:
    for label, rx in DOM:
        if re.match(rx, pkg):
            e = dom[label]
            break
    else:
        e = dom["Other: R8-renamed packages and top-level `com.waze.*` classes"]
    e[0] += c
    e[1] += m
    e[2] += nat
w(*table(["Feature domain", "Classes", "Methods", "Native methods"], [[k, n(v[0]), n(v[1]), v[2]] for k, v in sorted(dom.items(), key=lambda kv: -kv[1][0]) if v[0]], ["l", "r", "r", "r"]))
w("", f"All {n(fp['classes'])} first-party classes are assigned (first matching rule wins; packages are keyed by their first 3–4 segments — see `analysis/data/dex_summary.json → first_party.packages`). Largest readable packages:", "")
readable = [r for r in fp["packages"] if len(r[0].split(".")[-1]) >= 3 and not re.match(r"^com\.waze\.[a-z]{1,2}(\.|$)", r[0])]
w(*table(["Package", "Classes", "Methods", "Native"], [[f"`{short(r[0])}`", n(r[1]), n(r[2]), r[3]] for r in readable[:28]], ["l", "r", "r", "r"]))
w("")
w("### 5.3 Framework supertype census (direct subclasses; obfuscated bases are not counted)", "")
w(*table(["Supertype", "Direct subclasses"], [[f"`{s.strip('L;').replace('/', '.')}`", c] for s, c in dex["supertype_census"] if c >= 5], ["l", "r"]))
sc_ = dict(dex["supertype_census"])
w("", f"Only {sc_['Landroid/app/Activity;']} activities extend `android.app.Activity` and {sc_['Landroidx/activity/ComponentActivity;']} extend `ComponentActivity` directly — the rest sit behind R8-renamed base classes. {sc_['Landroidx/lifecycle/ViewModel;']} direct ViewModels, {sc_['Landroid/os/AsyncTask;']} legacy `AsyncTask` subclasses, `kotlinx.coroutines` pervasive.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 6 · Native layer — `libwaze.so`", "")
sec = {s["name"]: s["size"] for s in lib["sections"]}
w(*table(["Property", "Value", "Ev."], [
    ["File", f"`lib/arm64-v8a/libwaze.so` · {mb(lib['bytes'])} · ELF64 {lib['machine']} shared object · soname `{lib['soname']}` (armeabi-v7a twin: 62.7 MB)", "O"],
    ["Sections", f"`.rodata` {mb(sec['.rodata'])} · `.text` {mb(sec['.text'])} · `.eh_frame` {mb(sec['.eh_frame'])} · `.bss` {mb(sec['.bss'])} · `.data.rel.ro` {mb(sec['.data.rel.ro'])} · `protodesc_cold` {mb(sec['protodesc_cold'])} (protobuf descriptors)", "O"],
    ["Linked libraries (`DT_NEEDED`)", ", ".join(f"`{x}`" for x in lib["needed"]), "O"],
    ["Graphics / audio APIs", f"OpenGL ES ({lib['imports']['families']['OpenGL ES (gl*)']['count']} `gl*` imports incl. transform feedback → **GLES 3**), EGL ({lib['imports']['families']['EGL (egl*)']['count']}), OpenSL ES audio ({lib['imports']['families']['OpenSL ES']['count']}), `AAssetManager` (reads assets straight from the APK). **No Vulkan, no AAudio.**", "O"],
    ["JNI binding", f"{lib['exports']['static_JNI_symbols(Java_*)']} exported `Java_com_waze_*` symbols, **no `JNI_OnLoad`/`RegisterNatives`** → static, name-based lookup", "O"],
    ["Toolchain", "Android LLVM `clang 21.0.0` (r563880c) built with **`+pgo +bolt +lto +mlgo`** (a second `dev` toolchain without those flags is also recorded in `.comment`), linker `LLD google3-trunk`, NDK r29", "O"],
    ["Imports", f"{lib['imports']['count']} dynamic imports; sockets/DNS ({lib['imports']['families']['sockets / DNS']['count']}), pthread ({lib['imports']['families']['pthread']['count']}), dlopen family ({lib['imports']['families']['dl (dlopen/dlsym)']['count']})", "O"],
], ["l", "l", "c"]))
w("", "### 6.1 Embedded third-party components (string banners)", "")
w(*table(["Component", "Evidence (banner, as found)", "Hits"], [[k.replace("H3 / S2 geo", "S2 geometry"), f"`{v['example'].strip()}`", v["hits"]] for k, v in lib["embedded_library_banners"].items()], ["l", "l", "r"]))
w("", "Godot's own bundled libraries (glslang/SPIR-V, meshoptimizer, HarfBuzz, libwebp, zstd, brotli, libjpeg-turbo) account for several rows. **S2 geometry** (Google's spherical cell index) is the geo-indexing primitive. ICU 78 data is embedded (`icudt78`, 4,184 hits). BoringSSL, abseil and gRPC-core strings are present.", "")

w("### 6.2 Native source tree (from embedded `__FILE__` / log paths)", "")
sp = lib["source_paths"]
w(f"{n(sp['unique_files'])} unique source paths were recovered ({', '.join(f'{e}: {c}' for e, c in sp['extensions'])}).", "")
w(*table(["Directory (depth 4–5)", "Files", "What it is (inferred, **I**)"], [
    ["`third_party/waze/client/waze/src`", 520, "Core client — the original RoadMap/FreeMap C/C++ code base (map, navigation, real-time, UI helpers)"],
    ["`third_party/waze/client/cpp_modules/*`", 241, "Newer modular C++: `rendering_layer` 50 · `insights` 31 · `rendering` 24 · `tile_reader` 15 · `map_navigation` 13 · `realtime_insights` 11 · `userdb` 10 · `protobuf` 9 · `map_ads` 7 · `tile` 6 · `config` 6 · `map_labels` 6 · `waze_asks` 5 · `nav_connect` 5 · `navigation` 5 · `dispatch_utils` 4"],
    ["`third_party/waze/client/android-project/jni-protos`", 208, "`.proto` definitions of every JNI payload (→ `com.waze.jni.protos`)"],
    ["`third_party/waze/client_event_payloads/proto`", 764, "Telemetry/analytics event schemas (`stats` 691, `wrappers` 64)"],
    ["`third_party/waze/client_protos/proto`", 123, "Shared client↔server message schemas (`waze/`, `v2/`: e.g. Inbox, Lanes, Model, Types, Users)"],
    ["`third_party/godot/v4_4_waze/*`", 400, "A **forked Godot 4.4**: `scene` 151 · `core` 121 · `servers` 61 (rendering 35) · `drivers` 28 (GLES3 19) · `modules` 20 · `platform/android` 17"],
    ["`third_party/{protobuf,openssl/boringssl,absl,gloop}`", "~30", "Protobuf runtime, BoringSSL, abseil, Google-internal util"],
], ["l", "r", "l"]))
w("", "### 6.3 C++ namespaces recovered from RTTI (type-info names)", "")
w(f"{n(lib['cpp_rtti']['unique_types'])} distinct nested C++ type names. Top namespaces:", "")
w(*table(["Namespace", "Types", "Reading (inferred, **I**)"], [
    ["`linqmap::proto`", "1,106", "**LinQMap** — Waze's map/real-time data model (also `linqmap::geocoding`, 45)"],
    ["`stats::events`", 728, "Telemetry event messages"],
    ["`com::waze`", 658, "Java-facing protobuf messages (JNI)"],
    ["`waze::rendering`", 343, "Renderer, layers, labels"],
    ["`waze::insights` / `insightsserving` / `realtime_insights`", "107 / 99 / 33", "Traffic & road-insight engine"],
    ["`waze::map_ads`, `waze::wazegeoads`", "44 / 13", "Map advertising (branded pins)"],
    ["`waze::graphics`, `gfx_engine`, `canvas`, `generic_canvas`, `layers`", "41 / 27 / 24 / 8 / 13", "2-D/3-D scene abstraction"],
    ["`waze::userdb`, `waze::tile`, `waze::map`, `waze::map_objects`, `waze::location`, `waze::location_tracker`, `waze::alerts`, `waze::navigation`, `waze::navigate`, `waze::routing`, `waze::reroute_suggestion`, `waze::nav_connect`, `waze::waze_asks`, `waze::beacons`, `waze::replay`", "39 / 26 / 36 / 12 / 26 / 8 / 29 / 18 / 12 / 11 / 14 / 15 / 15 / 8 / 12", "Feature modules — the real navigation product"],
    ["`maps_tactile::directions`, `maps_gmm_snapping`, `pathfinder::crp`, `geostore`, `geo_serving_proto`, `geo_photo_service`", "149 / 103 / 55 / 302 / 117 / 160", "**Google Maps** routing/snapping/geostore message schemas embedded in the client"],
    ["`GLES3`, `RendererSceneCull`, `RendererCanvasRender`, `ShaderLanguage`, `RenderingDevice`", "39 / 15 / 14 / 13 / 10", "Godot rendering server types"],
    ["`icu_78`, `proto2`, `absl`, `spdlog`", "97 / 90 / 14 / 12", "Support libraries (ICU, protobuf, abseil, spdlog logging)"],
], ["l", "l", "l"]))
w("", f"**Protobuf schema files embedded** (`protodesc_cold`): {n(lib['proto_files']['unique'])} unique `.proto` names — Waze (`third_party/waze/*` ≈ 870), `geostore/base` 155, `geo/serving` 71, `maps/tactile` 66, `geo/photo` 65, `maps/gmm` 31 (snapping 17), `maps/pathfinder/crp` 17, `geo/vms` 11, `location/unified`, `storage/graph/bfg`. This is the vocabulary of the client↔server contract; the field-level definitions were **not** reconstructed.", "")
w("### 6.4 Other native libraries", "")
w(*table(["Library", "Size (arm64)", "Role"], [
    ["`libogg_opus_encoder.so`", "677 KB", "Ogg/Opus **voice recording** (custom prompts, voice commands) — own build, `src/` paths in the binary"],
    ["`libcrashlytics*.so` (4 files)", "≈13.3 MB", "Firebase Crashlytics NDK reporter"],
    ["`libimage_processing_util_jni.so`, `libsurface_util_jni.so`", "32 KB / 5 KB", "CameraX image/surface helpers"],
    ["`libandroidx.graphics.path.so`", "10 KB", "AndroidX path-measure accelerator"],
], ["l", "r", "l"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 7 · The Java ↔ native boundary", "")
w(f"{len(jni)} first-party classes declare **{jni_native}** `native` methods ({tot['native_methods']} counting all classes; {lib['exports']['static_JNI_symbols(Java_*)']} `Java_*` symbols are exported by the library). Most are `…NativeManager` facades whose methods end in `NTV` (usually with an `initNativeLayerNTV`); the rendering classes use `native…` method names. Largest:", "")
w(*table(["Class", "Native methods", "Examples"], [[f"`{short(j['class'])}`", j["native"], ", ".join(f"`{m}`" for m in j["methods"][:4])] for j in jni[:24]], ["l", "r", "l"]))
w("")
jd = collections.OrderedDict()
for j in jni:
    for label, rx in DOM:
        if re.match(rx, j["class"]):
            jd.setdefault(label, [0, 0])
            jd[label][0] += 1
            jd[label][1] += j["native"]
            break
    else:
        jd.setdefault("Other (core/system)", [0, 0])
        jd["Other (core/system)"][0] += 1
        jd["Other (core/system)"][1] += j["native"]
w("**JNI surface by product domain:**", "")
w(*table(["Domain", "Native classes", "Native methods"], [[k, v[0], v[1]] for k, v in sorted(jd.items(), key=lambda kv: -kv[1][1])], ["l", "r", "r"]))
w("", "**Protobuf messages crossing JNI, by domain** (`com.waze.jni.protos.<domain>`): " + ", ".join(f"{k} {v}" for k, v in feat["jni_protos_by_domain"][:22]) + ".", "")

w("### 7.1 Verified flows (REA/JADX decompilation, summarised as pseudocode)", "")
w("**Render tick** — `com.waze.map.opengl.WazeRenderer.l()` (REA evidence `" + rea["methods"]["WazeRenderer.l"] + "`):",
  "```text",
  "tick():",
  "  if stopped.get() or canvasTag.value is null: return false",
  "  renderThreadHost.run(prepare)            # GL-thread helper executes queued prep work",
  "  drawn = nativeRender(canvasTag)          # native engine renders one frame for this canvas",
  "  if drawn: run all one-shot post-frame callbacks under a lock; clear list",
  "  return drawn                             # (inferred) tells the host whether a frame was actually produced",
  "```",
  "**Surface lifecycle** — `h(Surface, w, h, mode)` creates the native surface on the render-thread host and *blocks until it is ready*; `i()` flushes on the render thread and calls `nativeFinalFlush(tag)`; resize and clear are queued the same way (evidence `" + rea["methods"]["WazeRenderer.h"] + "`, `" + rea["methods"]["WazeRenderer.i"] + "`). Natives: `nativeSurfaceCreated`, `nativeResize`, `nativeDraw`, `nativeRender`, `nativeClearCanvas`, `nativeDone`, `nativeFinalFlush`.",
  "",
  "**Location → core** — `LocationSensorListener.sendUpdateToNativeLayer` (evidence `" + rea["methods"]["Location.sendUpdateToNativeLayer"] + "`) → `createNativeLocationJNI` (`" + rea["methods"]["Location.createNativeLocationJNI"] + "`):",
  "```text",
  "fix = Android Location (provider GPS|NETWORK) + accelerometer[3] + gyroscope[3] + compass[3]",
  "msg = NativeLocationJNI {",
  "  position: IntPosition{lon, lat, altitude}   # integer fixed-point, not doubles",
  "  gpsTimeMs, accuracyMeters, speedMmSec, speedAccuracyMmSec,",
  "  steeringDegrees (bearing), steeringAccuracyDegrees,",
  "  sourceType: DEVICE | EXTERNAL_DEVICE (car GPS), provider: GPS | NETWORK,",
  "  injectedBySoftware: LocationCompat.isMock(location),   # mock-location flag",
  "  accelerometer, gyroscope, compass }",
  "notifyLocationNTV(msg.toByteArray())                   # one JNI call, one byte[]",
  "```",
  "Raw `LocationManager` + `SensorManager` are used (not the Fused provider); `GeomagneticField` corrects magnetic declination; a watchdog stops updates; there are separate \"device filtering\" and \"non-device filtering\" flows; `Car-GPS` is a distinct source.",
  "",
  "**Networking** — `NetworkManager` (evidence `" + rea["classes"]["NetworkManager"] + "`) owns an OkHttp `CookieJar` and a **prioritised request queue** (queue ids, priorities, auth types, transaction ids, \"abort all queue items\"); the native core produces requests and Java executes them (transport specifics such as HTTP/2 were not verified). `GrpcCallerNativeManager` + `WazeNetworkGateway` bridge **gRPC** calls the same way. (**I**, medium confidence — the request path itself was not decompiled.)",
  "",
  "**Map camera API exposed to the UI** (native methods on `MainCanvasDelegatorImpl`, evidence `" + rea["classes"]["MainCanvasDelegatorImpl"] + "`, and `WazeMapNativeManager`): `CenterOnMe`, `CenterOnPosition`, `ShowOverview`, `SetCompassFixed`, `UpdateMarginsPixels`, `UpdateUserLocationInsets`, `SetUserLocationOffset`, `ShowNavigationArrowOnSegment`, `ShowDarkOverlay[WithHighlight]`/`ClearDarkWithHighlight`, `DrawClosurePreview`, `PerformZoomIn/Out`, `UpdateMapBounds`, `UpdateMapContent/Configuration`, `GenerateEtaLabelPositions` (ETA labels on alternative routes). Several **canvases** coexist and are addressed by a string tag (`MainCanvasSwapperNativeManager.prepareGenericCanvasForSwappingNTV` / `restoreToMainCanvasNTV`) — main map, closure map, isolated/preview canvases, car display.",
  "",
  "**Navigation** — `NavigationServiceNativeManager`: `startNavigation`, `startNavigationOnRouteById`, `selectAlternativeRoute`, `handleRoutingUpdate`, `handleRerouteSuggestion`. `NavigationInfoNativeManager`: `getNavigationItems` (maneuver list), `getNavigationLanes`, `forceLanesEarlyDisplay`, `getMetersToCrossSegment`, `getMetersElapsedSinceSegment`, `isNearingDest`, `formatEtaClockString`, `updateNavigationResult`.",
  "",
  "**Voice** — `SoundNativeManager`: `getPromptDefinitions`, `getFileForPromptType`, `getPathForPrompt`, `playSoundFile`, `playTts`, `shouldMute`, `downloadPromptSet`, `getCustomPromptSet`, `prepareEditCustomPromptSet`, `saveCustomPrompt`, `finishEditCustomPromptSet`, `initiateUploadSequence`, `removeSetFromUser`. `TtsNativeManager`: `getSelectedTtsVoice`, `getTTSKeyTranslation`, `onCacheReady`, `onTtsDownloadComplete`.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 8 · Rendering stack", "")
w("Three layers draw the map (all native, all GLES 3):", "",
  "1. **Base map canvas** — vector map drawn by Waze's own engine, styled by a **Lua skin** (§8.1).",
  "2. **Overlay scenes** — markers, pucks, route effects drawn by an embedded **Godot 4.4 scene graph** (§8.2).",
  "3. **UI chrome** — Compose/Views *above* the map surface (ETA bar, instruction banner, buttons).", "")
w("### 8.1 Lua map skin (`assets/res/skins/default`)", "")
sk = assets["skins"]
w(f"{n(sk['files'])} files · {mb(sk['bytes'])}: {sk['png_total']} PNG ({sk['retina_variants']['@2x']} `@2x`, {sk['retina_variants']['@3x']} `@3x` variants) — 100 alert icons, 131 \"mood\" avatars, route/pin sprites — plus **12 Wavefront `.obj` 3-D models** ({len(sk['car_models_obj'])} vehicle skins + 2 GPS-state arrows) and {len(sk['lua_files'])} Lua files (`skin_structure.main.lua`, `skin_values.{{day,night}}.lua`, editor and experiment variants, five helper scripts for parsing/validation).", "")
w(f"`skin_structure.main.lua` ({sk['structure_lines']:,} lines) declares **{len(sk['map_categories'])} `Category(...)` blocks**, each with a base `MinZoom` style and **{sk['zoom_blocks']} `Zoom(n)` + {sk['last_zoom_blocks']} `LastZoom(n)` overrides** over {len(sk['zoom_values_used'])} zoom breakpoints ({sk['zoom_values_used'][0]} … {sk['zoom_values_used'][-1]}; Waze's own scale, larger = further out). Per-category properties: `color`, `thickness`, `border_color/width`, `label_visibility` (`all|shield_only|none`), `label_size/color/bgcolor/bold/uppercase`, `shield_scale_factor`. Global tables: `FontSizes` {sk['font_sizes']}, `ShieldScaleFactors` {sk['shield_scale_factors']}. Colour *values* live in `skin_values.day|night.lua` (palette of {sk['palette_roles']['day']} / {sk['palette_roles']['night']} named colours).", "")
cats = sk["map_categories"]
_g = [("Road network", ["Freeways", "Primary", "Secondary", "Highways", "Streets", "Private", "4X4 Trails", "Ramps", "Alleys"]),
      ("Rail, water, land & labels", ["Railroads", "Ferry", "Rivers", "Lakes", "Sea", "Islands", "Parks", "Cities", "Stations"]),
      ("Pedestrian & parking", ["Pedestrian", "Trails", "Walkway", "Parking", "ParkingLot", "ParkingLotPins", "VenueParkingLot"]),
      ("Navigation overlays", ["Navigation", "Navigation Arrow", "Stop Point", "Shared Navigation", "Shared Stop", "Route Snail", "Via Snail", "Shared Snail", "Shared Via Snail", "Recording", "Recorded"]),
      ("Route alternatives & preview", ["Route Preview Selected", "Route Preview Unselected", "Route Detour", "Alt Green Selected", "Alt Green Unselected", "Alt Blue Selected", "Alt Blue Unselected", "Alt Orange Selected", "Alt Orange Unselected"]),
      ("Misc: events, ads, carpool", ["GenericEvent", "AdPinBusinessName", "Carpool Ride", "Carpool Direct"])]
grp = [(g, [c for c in cs if c in cats]) for g, cs in _g]
assert sum(len(c) for _, c in grp) == len(cats), "skin category grouping out of sync"
w(*table(["Group", "Categories"], [[g, ", ".join(f"`{c}`" for c in cs)] for g, cs in grp], ["l", "l"]))
w("", f"3-D car models (`skins/default/cars/*.obj`): {', '.join(f'`{c}`' for c in sk['car_models_obj'])}. Plus `no_gps_model.obj`, `raw_gps_model.obj` for GPS-state arrows.", "")

w("### 8.2 Godot overlay scenes (`assets/res/godot/waze_map_scenes.pck`)", "")
w(f"**Format (O):** Godot pack format **{pck['pack_format']}**, engine **{pck['godot_version']}**, {pck['declared_files']} files, {pck['encrypted_files']} encrypted, flags {pck['flags']}; {pck['scene_like_files']} scene-like files, **{dict((e, c) for e, c, b in pck['by_extension']).get('.gdshader', 0)} `.gdshader` + 1 include**, **{pck['script_files']} GDScript files** (all logic is in C++). The pack was exported with Godot 4.4.1 tooling while the embedded runtime banner reads `v4.4.2.rc…` (a runtime newer than the pack format is compatible). Parsed by `pck_scan.py` — REA 6.7.0 (npm) could not open the pack (`unsupported binary format`); Godot PCK support is documented only on REA's `main` branch, so an independent parser was used.", "")
w(*table(["Extension", "Files", "Bytes"], [[e, c, n(b)] for e, c, b in pck["by_extension"]], ["l", "r", "r"]))
w("", "**Scene inventory** (top-level groups):", "")
pk = {r[0]: r[1] for r in pck["by_top_dir"]}
w(*table(["Group", "Scenes / resources"], [
    ["Alerts on the map", "`Alerts3D` (15), `AlertGlow2D` (3), `AlertGlow3D` (3), `OverviewAlertsAnimation` (10), `PermanentHazard`, `SpeedCamera` (body + rectangular/square badge), `TrafficLight`, `TollBooth`, `Railroad`, `TrafficPin`, `hazard`, `alert_pin_badge_{capsule,circle}`, `alert_pin_medium_{frame,icon}_part`, `pulse_scene`"],
    ["POI pins", "`AdPin` (sponsored), `ParkingPin` (regular / priced), `ExternalPoi` (rectangular / circular), `Flag` (destination chequered flag), `Home`, `Work`, `Wazer`, `map_marker`, `small_marker`, `large_marker`"],
    ["User & guidance", "`NewUserLocation` (puck) with `user_location` + `user_location_shadow` shaders, `accuracy_radius` shader, `GuidanceArrow`, `ArrowIndicator`, `Speedometer`, `Pill`, `DarkenHighlight`, `Loader`"],
    ["Route / geometry shaders", "`polyline`, `lines`, `lines_border`, `simple_polygon`, `tile_poylgon`, `Immersive/immersive_line`, `Immersive/immersive_polygon`, `pulse_fill`, `pulse_outline` (2-D and 3-D)"],
    ["Scene scaffolding", "`main_scene`, `root`, `Small/Medium/LargeScene` (zoom-tiered scenes), `3DAtlas`, `Animated3DObject`, `DebugLayer`"],
    ["Fonts (embedded)", "NotoEmoji-Regular, NotoSansSC-SemiBold (CJK), Roboto-Bold → 8.35 MB (70 % of the pack)"],
    ["Textures", "37 `.ctex`: 12 **ETC2-compressed** atlases (shadow, colour atlas, destination flag, hazard splits) + `@3x` pin PNG imports"],
], ["l", "l"]))
w("", "Node/resource census inside the binary scenes (occurrences): " + ", ".join(f"{t} {c}" for t, c, f in pck["godot_type_census"][:14]) + ". The scenes are small **animated 3-D sprites** (quads and low-poly meshes with `AnimationPlayer`s, 161 `Animation` resources) — i.e. alert pins that pop, pulse and billboard on the map.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 9 · UI layer", "")
w("### 9.1 Toolkit mix", "")
w(*table(["Signal", "Value", "Ev."], [
    ["Layout XML files / distinct layouts", f"{ressum['layout_files']} / {ressum['layout_count']}", "O"],
    ["Root tags", ", ".join(f"{t.split('.')[-1]} {c}" for t, c in ressum["layout_root_tags"][:6]), "O"],
    ["Layouts hosting a `ComposeView`", f"{ressum['compose_view_layouts']}: " + ", ".join(f"`{x}`" for x in sorted(set(layouts["compose_view_layouts"]))), "O"],
    ["Compose runtime/UI classes in DEX", f"{n(dex['libraries'][1][1])} classes, {n(dex['libraries'][1][2])} methods; `ComposableSingletons$*` first-party classes: {tot['compose_singletons']}", "O"],
    ["Material", "`Theme.MaterialComponents.DayNight.NoActionBar` (Views) + Material 3 resources (`m3_*`, incl. *expressive* shape/button state lists, split-button) — Material Components is bundled", "O"],
    ["Custom design components", "`WazeTextView` (516 + 58 uses), `OvalButton` (83), `WazeButton` (23), `TitleBar` (27), `WazeEditText`, `PointsView`, `SettingsTitleText`/`WazeSettingsView` (settings tree), `com.waze.design_components.*`, `com.waze.sharedui.views.*`", "O"],
    ["Compose compiler on non-UI code", "`$stable` fields on classes such as `SoundNativeManager` → the Compose compiler plugin is applied module-wide", "O/I (REA)"],
], ["l", "l", "c"]))
w("", "### 9.2 Themes", "")
w("`Theme.Main` (parent `Theme.MaterialComponents.DayNight.NoActionBar`) · `Theme.Main.NoAnimation` · `Theme.SettingsActivity` · `Theme.SilkyActivity` (smooth activity transitions) · `Theme.Splash` → `.V27` → `.V29` → `.V33` → `.Actual` · `Theme.Transparent`, `Theme.TransparentFromBottom`, `Theme.DimmedFromBottomNoAnim` (sheet-style activities) · `UidAppTheme.*` / `InfraAppTheme.*` (**UID** design-system themes) · `Theme.CarMain`/`CarIsNightMode` (Android Auto). Day/night is resolved with `values-night` (93 colours have night variants).", "")
w("### 9.3 Colour system (observed tokens)", "")
cols = tokens["tokens"]["color"]


def col(nm, cfg="default", d=0):
    v = cols.get(nm)
    if not v:
        return None
    x = v.get(cfg) or v.get("default")
    if x and x.startswith("@color/") and d < 6:
        return col(x[7:], cfg, d + 1)
    return x


def hx(x):
    return ("#" + x[3:].upper()) if x and x.startswith("#ff") else (("#" + x[1:].upper()) if x else "—")


roles = [("primary", "primary"), ("brand_waze", "brand_waze"), ("on_primary", "on_primary"), ("background_default", "background_default"), ("background_variant", "background_variant"), ("surface_default", "surface_default"), ("hairline", "hairline"), ("report_police", "report_police"), ("report_hazard", "report_hazard"), ("report_jam", "report_jam"), ("report_closure", "report_closure"), ("report_chat", "report_chat"), ("report_gas", "report_gas"), ("report_place", "report_place"), ("Traffic1", "Traffic1 (light)"), ("Traffic2", "Traffic2"), ("Traffic3", "Traffic3"), ("Traffic4", "Traffic4 (standstill)")]
w(*table(["Token", "Day", "Night"], [[f"`{lbl}`", hx(col(k)), hx(col(k, "night"))] for k, lbl in roles], ["l", "c", "c"]))
w("", f"{len(cols)} colour entries in total (library colours included). Waze scale families: `Blue50…900`, `Green`, `Red`, `Orange`, `Yellow`, `Grey`, `BlueGrey`, `Purple100…900`, `WinterBlue`. Semantic `primary` is `@color/Blue500` (day) / `@color/Blue300` (night). Map skin (separate system): `base_default` `#0095FF`, `map_background` `#FAFCFA`, `freeways` `#8D949B`, `primary` roads `#A6ADB3`, `street` `#D2D7DB`, labels `#787878`.", "")
w("### 9.4 Typography, shape, elevation", "")
dim = tokens["tokens"]["dimen"]
def dv(k):
    v = dim.get(k, {}).get("default", "—")
    return v.replace(".000000", "")
w(f"**Fonts (O):** `ProximaNova` — 9 `.otf` weights (light, regular, semibold, bold, extrabold + italics) wired through a font-family XML — plus the **Roboto** family (14 TTF: black … condensed, slab). Proxima Nova is a commercial typeface; Aize must not ship it (see plan §6). Native map labels use their own sizes (`tiny 6 / small 8 / medium 10 / big 12 / huge 14`).  ",
  f"**Corner radii:** buttons small **{dv('button_small_corner_radius')}** · normal **{dv('button_normal_corner_radius')}** · large **{dv('button_large_corner_radius')}** · alerter/bottom alerter **{dv('alerter_corner_radius')}** · audio panel {dv('audio_panel_corner_size')} · car cards {dv('car_card_corner_radius')}.  ",
  f"**Elevation steps:** `card_elevation_0…5` = {', '.join(dv(f'card_elevation_{i}') for i in range(6))}; car widgets {dv('car_widget_elevation')}.  ",
  f"**Car UI sizes:** instruction text {dv('car_instruction_text_size')} / large {dv('car_instruction_large_text_size')}, instruction icon {dv('car_instruction_image_width')}, widget button height {dv('car_widget_button_height')}, ETA widget width {dv('car_eta_options_widget_width')}.", "")
w("### 9.5 Layout inventory (non-library, grouped by screen family)", "")
lay = sorted({l["name"] for l in layouts["layouts"]})
fam = [("Main map & ETA chrome", r"^(waze_main_activity|eta_|minimized_eta|map_|compass|zoom|fab|bottom_recenter|bottom_pill|pill_|you_are_here|traffic_bar|speedometer|events_on_route|points_marker|closure|cavnas)"),
       ("Navigation HUD & alerts", r"^(navbar|nav_|navigation_|instruction|alert|alerter|bottom_alerter|rtalerts|typing_while|end_of_drive|call_to_action|generic_takeover|generic_eta|tooltip|tiny_tooltip)"),
       ("Search & places", r"^(search|autocomplete|side_menu_search|address_item|destination_cell|add_|edit_place|place_|omni_select|history|favorites|name_favorite|gas_price|opening_hours|view_photo|photo_dialog)"),
       ("Trip overview & route cards", r"^(trip_overview|route_header|planned_drive|select_endpoint|resume)"),
       ("Reports", r"^(report_|sos_|map_report|bottom_sheet_grid)"),
       ("Settings, voice, profile", r"^(settings_|waze_settings|quick_settings|voice_|custom_prompt|moods|mywaze|temp_user|choose_account|onboarding|ob_dialog|settings)"),
       ("Auth & consent", r"^(auth_|gdpr|waze_uid_consent|phone_request|fingerprint|location_failed)"),
       ("Dialogs, sheets, generic UI", r"^(confirm_dialog|popup|base_bottom|bottom_choice|bottom_sheet|waze_dialog|waze_big|waze_horizontal|waze_radio|waze_switch|waze_wheel|waze_slide|waze_header|waze_hero|checkbox|progress|timer|button_timer|icon_button|large_|normal_|small_|image_button|title_bar|two_line|edit_text|empty_card|badge)"),
       ("Share & social", r"^(share|receive_share|view_share|inbox|live_drive|user_popup)"),
       ("Audio apps panel (music)", r"^audio_"),
       ("Debug / test", r"^(debug|test_)")]
rows, seen = [], set()
for label, rx in fam:
    names = [l for l in lay if re.search(rx, l) and l not in seen and not re.match(r"^(abc_|mtrl_|m3_|design_|material_|notification_|preference|select_dialog|custom_dialog|ime_|support_)", l)]
    seen.update(names)
    rows.append([label, len(names), ", ".join(f"`{x}`" for x in names[:14]) + (" …" if len(names) > 14 else "")])
w(*table(["Screen family", "Layouts", "Examples"], rows, ["l", "r", "l"]))
w("", f"First-party drawable/mipmap resources: **{n(feat['drawable_families_first_party']['total'])}** — {', '.join(f'{e or '(none)'} {c}' for e, c in feat['drawable_families_first_party']['by_ext'])} (**raster-heavy**: PNG at several densities; vectors are the minority). Biggest name families: " + ", ".join(f"{k} {v}" for k, v in feat["drawable_families_first_party"]["top"][:14]) + ".", "")

w("### 9.6 Motion system", "")
wa = [x for x in motion["anim"] if not re.match(r"^(abc_|btn_|mtrl_|design_|m3_|linear_indeterminate|fragment_|m3expressive)", x["name"])]
w(f"**Duration tokens in Waze-specific animations** ({motion['waze_specific_anim_count']} `anim` + {motion['waze_specific_animator_count']} `animator` resources; library/Material defaults excluded; references resolved through `@integer/…` and the framework's `config_{{short,medium,long}}AnimTime` = 200/400/500 ms): " + ", ".join(f"**{k} ms** × {v}" for k, v in motion["waze_specific_duration_histogram_ms"]) + ". Named integer tokens: `bottom_sheet_slide_duration` 150, `buttons_fade_animation_duration_ms` 200, `abc_config_activityDefaultDur` 220 / `ShortDur` 150, `m3_sys_motion_duration_*` (Material 3 ladder up to 800).", "")
w("**Easing curves** (all `pathInterpolator`, cubic-bézier(x1, y1, x2, y2)):", "")
rows = []
for i in motion["interpolator"]:
    a_ = i["attrs"]
    if "controlX1" in a_ and not str(a_["controlX1"]).startswith("@"):
        rows.append([f"`{i['name']}`", f"({a_['controlX1']}, {a_['controlY1']}, {a_['controlX2']}, {a_['controlY2']})", "**Waze-specific**" if i["name"].startswith("silky") else "Material"])
w(*table(["Interpolator", "cubic-bézier", "Origin"], rows, ["l", "l", "l"]))
w("", "**Waze-specific `anim` resources** (library/Material animations excluded; interpolators are Android framework constants unless prefixed `interpolator/`):", "")
nice = {"pop_in_dialog": "dialog pop-in: alpha 100 ms + scale 200 ms with overshoot", "pop_out_dialog": "dialog pop-out", "pop_in_event_on_route": "**event-on-route pop-in**: alpha 100, scale 200 + 300 ms, starts at +300 ms", "slide_up_silky": "slide up from 100 %p → 0 (**`silky_entrance`**)",
        "slide_down_silky": "slide down", "rotate_infinite": "infinite spinner", "flicker": "alpha flicker", "move_right_left": "nudge", "main_tooltip_show": "tooltip show", "contact_tooltip_show": "contact tooltip show", "grow_dialog": "dialog grow", "shrink_dialog": "dialog shrink", "stack_up": "stack up"}
rows = [[f"`{x['name']}`", ", ".join(str(d) for d in x["durations_ms"]) or "—", ", ".join(i.replace("android:", "").replace("interpolator/", "") for i in x["interpolators"]) or "—", nice.get(x["name"], "")] for x in sorted(wa, key=lambda x: x["name"])]
w(*table(["Resource", "Duration (ms)", "Interpolator", "Note"], rows, ["l", "l", "l", "l"]))
w("", "Page-transition families: `common_ui_slide_*` (500 ms; decelerate-cubic in, accelerate-cubic out), `main_slide_*` (200 ms), `rewire_slide_*` and `uid_slide_*` (400 ms = `config_mediumAnimTime`); `fragment_open/close_*` (300 ms) and `fragment_fade_*` (150 ms) are androidx defaults. 85 `anim` + 43 `animator` + 20 `interpolator` resources exist in total.", "")
w("**Lottie animations — 53 JSON files, 1.5 MB:**", "")
lot = sorted(motion["lottie"], key=lambda x: -x["bytes"])
w(*table(["Name (internal)", "Size", "Canvas", "fps", "Duration", "Layers"], [[f"`{l['name']}`", f"{l['bytes'] / 1024:.0f} KB", f"{l.get('w')}×{l.get('h')}", l.get("fps"), f"{l.get('seconds')} s", l.get("layers")] for l in lot[:16]], ["l", "r", "c", "r", "r", "r"]))
w("", "Themes of the remaining files: assistant/voice states (`Conversation ALL …` ×11, `Talking Loop`, `Speaking lines`, `new sound wave`, `Assistant badge …`), loaders (`Ghost_loader`, `Loader_02/03`, `Loading_1`), **report button** (`report_menu_button` ×2, 70×70, 5.1 s loop), **points/rewards** (`points_animation_with_text`, `confetti`, `Spark`), onboarding (`01_OB animation sequence`, 13 s), share (`Share_Lottie_ex`, `lottie/thumbsup/96dp`), and a seasonal splash (`_WAZE_Splash_… Oct26`). The `ai_agent_habub_*` raw resources are further assistant-state animations.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 10 · Screens and flows inventory", "")
w("Derived from activities (§4.2), layouts (§9.5), packages (§5.2) and string/ID vocabularies (§11). **I** = inferred grouping.", "")
w(*table(["#", "Screen / flow", "Evidence (class / layout)", "Notes"], [
    [1, "Splash → main", "`FreeMapAppActivity` (`Theme.Splash.Actual`), seasonal Lottie splash", "Android 12 splash + animated Lottie"],
    [2, "Onboarding, country, consent, sign-up/login", "`install.SelectCountryActivity`, `auth_*` (13), `waze_uid_consent_screen`, `gdpr_consent_bump`, `ob_dialog_*`, `signup*` drawables", "Email/password, account chooser, guest; privacy consent"],
    [3, "**Main map**", "`waze_main_activity` (Compose host), `map_frame_control`, `fab_layout`, `compass_button`, `zoom_controls`, `bottom_recenter_bar`, `map_report_button_view`", "Native map surface under Compose chrome"],
    [4, "Search (v2) & autocomplete", "`SearchV2Activity` (`search_v2_fragment`, ComposeView), `AutocompleteSearchActivity`, `side_menu_search_bar`, `search_result_pin_*`", "Category chips, along-route vs around-you, 3 providers (§11.4)"],
    [5, "Location preview / place card", "`LocationPreviewActivity`, `details_popup`, `place_photo_*`, `edit_place*`", "Photos, opening hours, services, parking/gas price"],
    [6, "**Route preview / trip overview**", "`TripOverviewActivity`, `trip_overview_*` (7 layouts, ComposeView), `route_header`, ETA labels via `nativeGenerateEtaLabelPositions`", "Up to 3 colour-coded alternatives (Alt Green/Blue/Orange), toll price, HOV"],
    [7, "**Navigation HUD**", "`navbar`, `instruction_view`, `eta_main_bar_layout`, `eta_control_panel_layout`, `eta_compact_bar_component_widget`, `speedometer`, `traffic_bar`, `events_on_route_view`, lanes via `getNavigationLanes`", "Compose ETA bar/control panel; native route/arrow"],
    [8, "Alerts on route (alerter pop-ups)", "`alerter_popup`, `alerter_layout`, `bottom_alerter_component_widget`, `alert_summary_view`, `alert_ticker`, `AlerterNativeManager`", "Pop-in animation `pop_in_event_on_route`"],
    [9, "**Report menu & flows**", "`report_menu` (+portrait/landscape), `report_generic*`, `report_closure_content`, `report_gas_price_content`, `ClosureMap`, `SosProvidersListActivity`, `reports_v2.presentation`, `ConversationalReporting*`", "Grid → sub-type → details; voice-driven (\"conversational\") reporting"],
    [10, "Alert comments / thanks", "`RtAlertsComments`, `rtalerts_comments_*`, `WazeAsksNativeManager` (\"Waze Asks\" questions to drivers)", "Confirm / not-there / comment"],
    [11, "Arrival & end-of-drive", "`end_of_drive_encouragement_popup`, `navbar_nearing_dest_photo`, parking suggestion (`ParkedHere`, `ParkingUpdateLocationActivity`)", "Destination photo, parking, points"],
    [12, "Planned drives & calendar", "`PlannedDriveActivity`, `planned_drive_*` (12), `CalendarApprovedActivity`, `settings_calendar_selection`", "Leave-time suggestions from events"],
    [13, "Favorites, history, home/work", "`FavoritesActivity`, `HistoryActivity`, `AddHomeWorkActivity`, `add_fav`, `name_favorite_layout`", ""],
    [14, "Share ETA / live drive", "`ShareHelpActivity`, `ViewShareDriveActivity`, `view_share_drive_layout`, `live_drive_participant_pin`, `sharedrive.*`", "Share link & friends"],
    [15, "Settings tree", "`SettingsMainActivity`, `settings_main`, `settings_page_mk2` (Compose), 54 setting ids (§11.1)", "Tree-driven, server/ config backed"],
    [16, "Voice selection / custom prompts", "`voice_selection_*`, `CustomPromptsRecordingActivity`, `CustomVoicesFallbackVoicePickerActivity`, `recorder_popup`", "Record own voice, fallback voice"],
    [17, "Moods, profile, points", "`MoodsActivity`, `mywaze`, `TempUserProfileActivity`, `points_marker*`, `moods` skin (131 PNG), `MoodManager` (13 natives)", "Avatar (\"mood\") system & gamification"],
    [18, "Inbox / notifications", "`InboxPreviewActivity`, `inbox_*`, `InboxNativeManager`", ""],
    [19, "Audio apps panel", "`audio_panel_*` (9 layouts), `sdk` (Audio Kit), Spotify `LoginActivity`", "Music controls inside the nav screen"],
    [20, "Speech recognition", "`SpeechRecognizerActivity`, `speech_recognizer_bottom_sheet`, `google_assistant` package", "Voice commands + Assistant integration"],
    [21, "Android Auto", "`WazeCarAppService`, `car_lib.*` (screens 151 classes), `car_*` dimens", "Car App Library templates"],
    [22, "Gas prices / nearby stations / EV", "`GasPriceReportActivity`, `NearbyGasStationsActivity`, `settings…ev_profile`, `gas_price_item`", "Gas type, EV connectors & networks"],
    [23, "Debug / internal", "`DebugConfigListActivity`, `config.ConfigValues`, `test_gps`", "Hidden config editor"],
], ["c", "l", "l", "l"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 11 · Feature inventory", "")
w("### 11.1 Settings tree (ids recovered from the DEX)", "")
ids = feat["settings_ids"]["all"]
w(f"{len(ids)} dotted ids; the complete tree is server/config-driven, so this is a **subset**. Sections: " + ", ".join(f"`{s.replace('settings_main.', '')}` ({c})" for s, c in feat["settings_ids"]["top_sections"]) + ".", "")
w("```text")
for i in ids:
    w(i.replace("settings_main.", "").replace(".", " › "))
w("```", "")
w("### 11.2 Native-UI string tables", "")
w(f"`assets/res/lang.eng` — **{n(feat['lang_keys']['count'])} `KEY=value` entries** (`DISPLAY_STRING_TRANSLATION_FILE_VERSION` header); Hebrew (920 KB) and Chinese (103 KB) tables ship, others are downloaded. Key families (by prefix): " + ", ".join(f"`{k}` {v}" for k, v in feat["lang_keys"]["top_families"][:12] if k.isupper() and len(k) > 2) + ". 86 Android string locales exist only for the ~285 platform-level strings; **the app's main UI text is not in `strings.xml`**.", "")
w("### 11.3 Community / report taxonomy (from settings ids, colours and key families)", "")
w("Report colours: police, hazard, jam, closure, chat, gas, place, crash (§9.3). Permanent-hazard alert toggles (settings ids): complex intersection, complex merge, highway crosswalk, lane ending, narrow bridge, railroad, raised crosswalk, school zones, sharp curve, shoulder ending, speed bump, speed-limit decrease, toll booth, traffic lights; plus `cameras`. Reroute-suggestion strings (`REROUTE_*`, 108 keys) are templated around *saves N minutes and avoids {hazard|road closure|accident|…}*. Voice earcons: `alert_1`, `ping`, `ping2`, `reminder`, `bonus`, `message_ticker`, `speed_limit`, `feedback_on_alerts`.", "")
w("### 11.4 Search configuration (`assets/res/search_conf`)", "")
sc = assets["search_conf"]
w(f"Binary text-buffer ({sc['bytes']:,} bytes) generated server-side. **Providers:** `waze` (\"Waze\"), `googlePlaces` (\"Google Places\"), `foursquareexplore` (\"Foursquare\"). **Modes:** *Around You*, *Along Route*. **Category ids:** " + ", ".join(f"`{c}`" for c in sc["category_ids_seen"] if c not in ("textbuf", "max_distance_meters", "route_policy", "foursquareexplore") and "address_search" not in c) + ". (The build-machine path embedded in the file is not reproduced.)", "")
w("### 11.5 Other feature signals", "")
w("Moods (258 `MOOD_*` keys, 131 PNG) · 3-D vehicle skins (10) · planned drives · HOV lanes (`SettingsHOVActivity`, `eta_widget_hov_suggestion`) · tolls (`NavigateTollPriceInformation`) · EV profile · \"Hoy No Circula\" (Mexico City restriction) · license-plate setting · parking suggestions · Waze Asks · beacons (BLE) · Audio Kit/Spotify · Google Assistant App Actions · trip suggestions / personalisation · ads (`map_ads`, sponsored pins, `AutocompleteAdBackground`) · Waze SDK service (`com.waze.sdk.SdkService`).", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 12 · Voice and audio", "")
sd = assets["sound"]
vs = assets["sound_vs_community_voicepack_schema"]
w(*table(["Directory", "Files", "Size", "Contents"], [
    ["`sound/eng/`", sd["eng"]["files"], f"{sd['eng']['bytes'] / 1e6:.1f} MB", "English prompt set (distance words, turns, exits, alerts, units)"],
    ["`sound/heb/`", sd["heb"]["files"], f"{sd['heb']['bytes'] / 1e6:.1f} MB", "Hebrew prompt set (same names)"],
    ["`sound/common/`", sd["common"]["files"], f"{sd['common']['bytes'] / 1e6:.1f} MB", "Language-independent earcons: `ping`, `ping2`, `click`, `reminder`, `rec_start/end`, `points_animation`, `speed_limit`, `TickerPoints`, `beepbeep`, `voice_guidance_{off,alerts,beep,brief,full,smart}`, `conversational_{minimalist,popcorn}_{mic_on,mic_off,confirmation,error}`"],
], ["l", "r", "r", "l"]))
w("", "### 12.1 Cross-reference with the community voice-pack archive", "")
w(f"The repository [`pipeeeeees/waze-voicepack-links`](https://github.com/pipeeeeees/waze-voicepack-links) (GPL-3.0; a community **archive of links** to custom Waze voice packs hosted on Waze's CDN — the audio itself is not in the repo) documents the file schema a custom pack must use: **{vs['community_valid_names']} MP3 names**, total pack size **≤ 0.8 MB** (limit set by Waze), uploaded as a tar.gz referenced by `waze.com/ul?acvp=<uuid>`. Result of comparing it with this APK:", "")
w(f"- **All {len(vs['in_both'])} community names exist in the APK's built-in English set** — the community schema is the user-replaceable subset.", f"- The APK's `eng/` set has **{len(vs['only_apk_eng'])} additional files** the community schema does not cover: " + ", ".join(f"`{x}`" for x in vs["only_apk_eng"]) + " (unit words, `StartDrive` variants, earcons).",
  f"- Prompt families in the schema: distances (`200`, `400`, `800`, `1500` + `…meters`, `1000meters`), connectors (`AndThen`), turns (`TurnLeft/Right`, `KeepLeft/Right`, `Straight`, `uturn`), exits & roundabouts (`ExitLeft/Right`, `Roundabout`, `First…Seventh`), arrival (`Arrive`), alerts (`ApproachAccident/Hazard/RedLightCam/SpeedCam/Traffic`, `Police`), start-of-drive greetings (`StartDrive1…9`), reroute chime (`TickerPoints`).",
  "", "### 12.2 Text-to-speech and custom prompts", "",
  f"- **TTS phrase table:** `key_value_tts_strings.txt` — {feat['tts_keys']['count']} `NAV_TTS_TEXT_*` keys (groups: " + ", ".join(f"{k} {v}" for k, v in feat["tts_keys"]["groups"][:14]) + ").",
  "- `voices_was_tts.csv` lists two voice ids (`local_nuance_8_mp3_Samantha_Female`, `…_Tom_Male`, en-US) — a Nuance-based, MP3-delivered TTS voice family (bit-rate and delivery path not verified); the app also queries the system `TTS_SERVICE`.",
  "- **Custom prompts:** `CustomPromptsRecordingActivity` + `SoundNativeManager.{prepare,save,finish}…CustomPromptSet` + `initiateUploadSequenceNTV` + `libogg_opus_encoder.so` (Opus). `CustomVoicesFallbackVoicePickerActivity` picks the voice used for prompts the user did not record.",
  "- Modes are earcon-backed: `voice_guidance_off | alerts | beep | brief | smart | full`.", "")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 13 · Network and API surface", "")
w("Observed endpoints are listed so the architecture is understandable. **They are Waze's private, authenticated services; nothing here is a recipe for calling them, and Aize does not use them (see plan §7).**", "")
HOST = {
    "rt.waze.com": ("Real-time server (live traffic / reports sync)", "private"), "gapi.waze.com": ("API gateway", "private"), "cres.waze.com": ("Client resources", "private"), "cresg.waze.com": ("Client resources (global)", "private"),
    "storagegateway-row.waze.com": ("Storage gateway (rest-of-world region)", "private"), "voice-prompts.waze.com": ("Voice prompt sets (CDN)", "public CDN"), "client-assets.waze.com": ("Client assets (CDN)", "public CDN"),
    "venue-image.waze.com": ("Place images", "public CDN"), "photos.waze.com": ("User/place photos", "public CDN"), "mobile-web.waze.com": ("Embedded web pages", "web"), "movies.waze.com": ("Video content", "web"),
    "ads-resources.waze.com": ("Ads resources", "ads"), "adsassets.waze.com": ("Ads assets", "ads"), "sdk.waze.com": ("SDK portal", "web"), "waze.to": ("Short links", "web"), "www.waze.com": ("Website, Live Map, `/ul` deep links", "web"), "waze.com": ("Website / deep links", "web"),
    "gcp.wazestg.com": ("Staging", "internal"), "rt.gcp.wazestg.com": ("Staging real-time", "internal"), "stgweb.waze.co.il": ("Staging web", "internal"),
}
dh = dict((h, c) for h, c in dex["urls_top_hosts"])
nh = dict((h, c) for h, c in lib["urls"]["top_hosts"])
rows = [[f"`{h}`", r, a, dh.get(h, 0), nh.get(h, 0)] for h, (r, a) in HOST.items() if h in dh or h in nh]
w(*table(["Host", "Role (inferred)", "Access", "refs in DEX", "refs in native"], rows, ["l", "l", "l", "r", "r"]))
w("", "Third-party hosts: Firebase (`firebaseappcheck`, `firebaseremoteconfig[realtime]`, `fcmregistrations`, `firebase-settings.crashlytics.com`, `firebaseinstallations`), Google (`googleapis.com`, `accounts.google.com`, `play.google.com`, `pagead2.googlesyndication.com`, `www.googleadservices.com`), `support.google.com` / `policies.google.com` (help & policy links), `bilans-ges.ademe.fr` (French CO₂ emissions reference), `www.gob.mx` (Mexico). No cleartext (`http://`) endpoint is allowed by the manifest (`usesCleartextTraffic=false`).", "")
w("### 13.1 Protocol layers", "")
w(*table(["Layer", "Observation", "Ev."], [
    ["Client ↔ server", "(a) a queued HTTP request channel executed by OkHttp for the native core (`NetworkManager`), (b) **gRPC** driven from native (`GrpcCallerNativeManager`, `WazeNetworkGateway`; grpc-java service files shipped), (c) protobuf everywhere", "O/I"],
    ["Real-time ('RT') channel", "host `rt.waze.com`; native `waze::realtime`, `waze::realtime_insights`; `RealtimeNativeManager.getServerGeoConfig/getCoreVersionAndServer`", "O/I"],
    ["Push", "FCM (`com.google.android.c2dm.permission.RECEIVE`, `NativeManager` pushes the GCM token into the core)", "O"],
    ["Remote config / flags", "`ConfigManager` natives (`getConfigValueBool/Int/Long/String`, sticky/locked values, beta flag) + Firebase Remote Config + Phenotype", "O"],
    ["Telemetry", "764 event-payload protos (`stats::events`), `StatsReporterNativeManager`, `MetricsReporterNativeManager`, `AdEventsReporterNativeManager`, Room-backed `stat_container` queue (§14)", "O"],
    ["Third-party app interop", "`waze.com/ul` deep links; **Waze Audio Kit** (`com.waze.sdk.audio.ACTION_INIT`, `SdkService`) for music apps; Spotify SDK; Google Assistant App Actions", "O"],
], ["l", "l", "c"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 14 · Local storage and configuration", "")
w(*table(["Store", "Observation"], [
    ["Room `StatsDatabase` v3", "single table `stat_container(identifier INTEGER, stat BLOB, created_date_millis INTEGER, stat_type TEXT)` — a durable queue for telemetry payloads; all other state is held by the native core"],
    ["Native storage", "`waze::userdb` (user data), `waze::tile` / `tile_reader` (map tiles), SQLite embedded in `libwaze.so` (`SQLite format 3` banner)"],
    ["SharedPreferences", "`WAZE MAIN PREFS` (seen in `NativeManager`)"],
    ["Language tables", "`lang.eng/heb/chinese` (key=value), downloaded per-language updates, `DISPLAY_STRING_TRANSLATION_FILE_VERSION`"],
    ["Config", "`ConfigManager` (native config store with locked/sticky values), `search_conf`, `phenotype/*.binarypb`"],
    ["ART profile", "`assets/dexopt/baseline.prof` (10,192 B) + `baseline.profm` (249 B)"],
], ["l", "l"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 15 · Third-party SDKs and platform services", "")
w(*table(["Area", "What was found", "Ev."], [
    ["Firebase", "Crashlytics (NDK libs; collection disabled by default), Performance (logcat flag), Remote Config (+realtime), App Check, Installations, Messaging (FCM), Auth/`SignInHubActivity`", "O"],
    ["Google Play services", "Ads (AdMob application id meta-data, `pagead2.googlesyndication.com`), Wallet, Auth/Credential Manager + Identity (`androidx.credentials.playservices.*` hidden activities), Phenotype, Play Core + Integrity", "O"],
    ["Google Assistant", "`AppIntegrationServiceGrpc` (13 un-renamed classes), `google_assistant` package, `GoogleAssistantNativeManager` (app-context encoding)", "O"],
    ["Media & camera", "Media3/ExoPlayer (2,824 classes), CameraX (3,754 classes; `camera_preview`, photo reports), Glide (435), Lottie (235)", "O"],
    ["Spotify", "Spotify Android auth SDK (`LoginActivity`), `queries` for `com.spotify.music`, Waze Audio Kit for in-nav music controls", "O"],
    ["Persistence & background", "Room (532), DataStore (788), WorkManager (622)", "O"],
    ["Networking", "OkHttp/Okio (170), grpc-java (renamed), Jackson (1,051)", "O/I"],
    ["Car", "Car App Library (779 classes, API level 9; min 5)", "O"],
], ["l", "l", "c"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 16 · Performance-engineering signals (collected)", "")
w("These are the observations that explain why Waze feels smooth, and which the Aize plan turns into requirements:", "")
w(*table(["#", "Signal (observed)", "Where", "Takeaway"], [
    [1, "Native render thread owns an EGL context created from a raw `Surface`; Java never draws the map", "`WazeRenderer`, `NativeCanvasRenderer`, `libEGL/libGLESv3`", "Use a surface-backed native renderer; keep Compose off the map's critical path"],
    [2, "`nativeRender()` returns a *drawn?* boolean — suggests on-demand frames rather than a fixed loop (**inferred**; the caller was not decompiled)", "REA evidence on `WazeRenderer.l`", "Design for render-on-dirty: it saves battery and CPU"],
    [3, "Post-frame one-shot callbacks run only after a drawn frame", "same", "Cheap hook for UI synchronisation/screenshots"],
    [4, "Fixed-point integer positions and mm/s speeds across JNI; one `byte[]` per fix", "`NativeLocationJNI`", "No float formatting/parsing; one coarse JNI call per sample"],
    [5, "Protobuf over JNI (3,161 generated classes) rather than many primitive calls", "`com.waze.jni.protos`", "Typed, batched interop (UniFFI/protobuf in Aize)"],
    [6, "Static JNI symbol binding (716 `Java_*` exports, no `RegisterNatives`)", "`libwaze.so`", "`RegisterNatives`/UniFFI avoid first-call lookups"],
    [7, "PGO + BOLT + LTO + MLGO native build; NDK r29", "`.comment`, `.note.android.ident`", "Rust: `lto=fat`, `codegen-units=1`, PGO; consider BOLT"],
    [8, "ART baseline profile shipped", "`assets/dexopt/baseline.prof`", "Baseline + startup profiles in CI"],
    [9, "R8 minification incl. libraries; resource-path shortening", "DEX names, `res/*`", "R8 full mode + resource shrinking"],
    [10, "Zoom-dependent LOD in the skin: 94 `Zoom()` overrides for line width/colour/label size", "`skin_structure.main.lua`", "Zoom-interpolated style expressions"],
    [11, "ETC2-compressed GPU textures for map sprites", "Godot pack `.etc2.ctex`", "Compressed textures for sprites/atlases"],
    [12, "Network requests are queued with priorities and aborted in bulk", "`NetworkManager`", "Prioritised, cancellable request scheduler"],
    [13, "Sensor fusion (accelerometer/gyro/compass) feeds the native matcher together with the fix", "`LocationSensorListener`", "Fuse motion sensors for heading stability & dead reckoning"],
    [14, "`largeHeap=true`, `hardwareAccelerated=true`", "manifest", "(Aize should not need `largeHeap`)"],
    [15, "**Weaknesses to beat:** raster-heavy icon set (3,073 PNG), 131 MB universal APK with two ABIs, game engine + 8 MB CJK font in the pack, `supportsRtl=false`, legacy `AsyncTask`s", "§2–§9", "Vectors, AAB splits, no engine, RTL-ready, coroutines"],
], ["c", "l", "l", "l"]))
w("")

# ---------------------------------------------------------------------------------------------------------------------
w("---", "", "## 17 · Limitations, unknowns, and how to go deeper", "")
w("### 17.1 What was **not** done (and why)", "",
  "- **Full-APK decompilation.** Loading the whole 60,430-class APK into JADX was **OOM-killed** on the 1 GiB analysis VM (kernel `Out of memory: Killed process … (java)`, REA reported `cancelled`). The same REA/JADX tools worked on **single-dex slices** (≈23 s, ≈410 MB peak); that is how §7.1 was verified. Cross-dex references are therefore unresolved in those outputs. A full pass most likely needs a ≥ 3 GiB machine (e.g. a \"Large\" sandbox at 3× the compute cost); it was deliberately **not** started without the owner's go-ahead.",
  "- **No dynamic analysis** (no emulator run, no traffic capture, no Frida) — nothing in this report describes runtime behaviour beyond what the code/data proves statically.",
  "- **Godot scenes** were inventoried, not decoded node-by-node; `.scn` binary resource parsing is a possible follow-up.",
  "- **Protobuf field layouts** were not reconstructed (only file names/namespaces).",
  "- **Native code** was not disassembled; `libwaze.so` conclusions come from ELF metadata, imports/exports, RTTI and embedded strings.",
  "- Library census is a lower bound because R8 renamed library packages.",
  "- REA 6.7.0 (npm) lacks the Godot PCK reader documented on `main`; the pack was parsed with `pck_scan.py` instead.", "",
  "### 17.2 Open questions that would change the plan if answered", "",
  "1. How much of routing is computed on-device vs. server-side (the client embeds Google `maps/tactile`, `pathfinder/crp` and `gmm/snapping` message schemas)? → needs native analysis or traffic observation (not attempted).",
  "2. The exact frame pacing of the native renderer (`Choreographer` vs internal timer) → full-APK JADX on `WazeMapView`/`MapView` hosts.",
  "3. Field definitions of `client_protos` (Inbox, Lanes, Model, Types, Users) → descriptor extraction from `protodesc_cold`.",
  "4. Which Compose screens are fully Compose vs Compose-in-Views beyond the 16 `ComposeView` layouts → full-APK analysis.", "",
  "### 17.3 Reproduce / extend", "",
  "```bash",
  "# 1) install REA (CLI) and the skill; supply the JADX jar (see analysis/README.md)",
  "# 2) run the whole pipeline on any Waze APK:",
  "bash analysis/tools/run_all.sh /path/to/waze.apk analysis/data",
  "# 3) regenerate this document",
  "python3 analysis/tools/render_structure_report.py analysis/data docs/01-waze-apk-structure-report.md",
  "```", "",
  "---", "",
  "### Appendix A — REA evidence index", "")
rows = [["APK inventory (`inspect-artifact`)", f"`{rea['apk_inventory']['evidence_id']}`", "whole-APK graph, 6,774 occurrences"]]
for k, v in rea["methods"].items():
    rows.append([f"`inspect-android-method` · `{k}`", f"`{v}`", "single-dex slice, JADX 0.7.1"])
for k, v in rea["classes"].items():
    rows.append([f"`inspect-android-class` · `{k}`", f"`{v}`", "single-dex slice, JADX 0.7.1"])
w(*table(["REA command · target", "Evidence ID", "Scope"], rows, ["l", "l", "l"]))
w("", "### Appendix B — Data files (`analysis/data`)", "")
w(*table(["File", "Content"], [
    ["`manifest.json`", "decoded manifest (components, intent filters, permissions; secrets redacted)"], ["`inventory.json`, `apk_files.csv`", "archive buckets, per-file sizes"], ["`signing.json`", "signing schemes + certificate fingerprint"],
    ["`dex_summary.json`", "classes, packages, libraries, JNI classes, URLs/hosts"], ["`libwaze_summary.json`, `libogg_opus_summary.json`", "ELF facts, imports, banners, source tree, RTTI, protos"],
    ["`pck_summary.json`, `pck_files.csv`", "Godot pack directory"], ["`resources_summary.json`, `resource_files.csv`, `design_tokens.json`", "resource table, shortened-path map, colours/dimens/styles/fonts"],
    ["`motion.json`, `layouts.json`", "animations/interpolators/Lottie, layout inventory"], ["`features.json`, `assets.json`", "settings ids, key families, TTS keys, skins, sounds, search config"],
    ["`rea_evidence_index.json`", "REA evidence ids and timings"],
], ["l", "l"]))
open(OUT, "w").write("\n".join(L) + "\n")
print("wrote", OUT, len(L), "lines")
