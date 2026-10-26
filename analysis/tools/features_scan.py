#!/usr/bin/env python3
"""Feature-vocabulary scan: what product areas does the APK contain? (static; names/keys only)

Sources: DEX string pools (settings-tree ids), assets/res/lang.eng (translation *keys*),
assets/res/key_value_tts_strings.txt (TTS phrase keys), the Lua map skin (section names and a
trimmed palette), drawable name families, and preserved first-party class names.
Translation *values* are not copied.
"""
import collections
import json
import os
import re
import struct
import sys
import zipfile


def uleb(buf, off):
    r = s = 0
    while True:
        b = buf[off]
        off += 1
        r |= (b & 0x7F) << s
        if b < 0x80:
            return r, off
        s += 7


def dex_strings(buf):
    n, o = struct.unpack_from("<2I", buf, 56)
    for off in struct.unpack_from("<%dI" % n, buf, o):
        _, p = uleb(buf, off)
        yield buf[p:buf.find(b"\0", p)].decode("utf-8", "replace")


def main(apk, out_dir, names_txt, res_files_csv):
    z = zipfile.ZipFile(apk)
    out = {}
    # 1) settings tree ids / other dotted id families from dex strings ------------------------------
    settings, dotted = set(), collections.Counter()
    idre = re.compile(r"^[a-z][a-z0-9_]{2,40}(?:\.[a-z0-9_]{2,48}){1,6}$")
    for n in sorted(x for x in z.namelist() if re.fullmatch(r"classes\d*\.dex", x)):
        for s in dex_strings(z.read(n)):
            if s.startswith("settings_") and idre.match(s):
                settings.add(s)
            elif idre.match(s) and not s.startswith(("android.", "androidx.", "java.", "kotlin.", "com.", "org.", "io.", "javax.", "dalvik.", "libcore.", "sun.", "net.")):
                dotted[s.split(".")[0]] += 1
    tree = collections.defaultdict(list)
    for s in sorted(settings):
        tree[".".join(s.split(".")[:2])].append(s)
    out["settings_ids"] = {"count": len(settings), "top_sections": sorted(((k, len(v)) for k, v in tree.items()), key=lambda r: -r[1])[:60],
                           "all": sorted(settings)}
    out["dotted_id_roots"] = dotted.most_common(40)

    # 2) lang.eng key families (keys only) -----------------------------------------------------------
    keys = []
    for line in z.read("assets/res/lang.eng").decode("utf-8", "replace").splitlines():
        if "=" in line:
            k = line.split("=", 1)[0].strip()
            if k:
                keys.append(k)
    fam = collections.Counter()
    for k in keys:
        parts = k.split("_")
        fam[parts[0]] += 1
    out["lang_keys"] = {"count": len(keys), "top_families": fam.most_common(80)}
    taxonomy = {}
    for label, rx in {
        "report/alert": r"^(REPORT|ALERT|RTALERT|HAZARD|POLICE|ACCIDENT|TRAFFIC|CLOSURE|CAMERA|SPEED_CAM|ROADKILL|POTHOLE|CONSTRUCTION|WEATHER)",
        "navigation": r"^(NAV|NAVIGATE|ROUTE|ROUTING|ETA|LANE|EXIT|TURN|ROUNDABOUT|RECALC|REROUTE)",
        "search/places": r"^(SEARCH|PLACE|PLACES|FAVORITE|HOME|WORK|RECENT|PARKING|GAS|EV|CHARGING)",
        "social/gamification": r"^(MOOD|POINTS|RANK|WAZER|FRIEND|SHARE|SOCIAL|INBOX|CHAT|MEETING|LIVE_DRIVE)",
        "voice/sound": r"^(VOICE|SOUND|TTS|PROMPT|AUDIO|SPEECH|VOLUME|MUTE)",
        "settings": r"^(SETTINGS|PREF|CONFIG)",
        "account/onboarding": r"^(LOGIN|SIGN|REGISTER|ACCOUNT|AUTH|WELCOME|ONBOARD|PRIVACY|CONSENT|GDPR|PROFILE)",
        "ads/commercial": r"^(AD|ADS|PROMO|SPONSOR|COUPON|BRAND)_",
        "offline/updates": r"^(OFFLINE|UPDATE|DOWNLOAD|MAP_UPDATE|SYNC)",
        "car/hov/vehicle": r"^(CAR|HOV|VEHICLE|TOLL|MOTORCYCLE|TAXI|CARPOOL|PUBLIC)",
    }.items():
        taxonomy[label] = sum(1 for k in keys if re.match(rx, k))
    out["lang_taxonomy_counts"] = taxonomy

    # 3) TTS phrase keys ------------------------------------------------------------------------------
    tts = [l.split("=", 1)[0] for l in z.read("assets/res/key_value_tts_strings.txt").decode("utf-8", "replace").splitlines() if "=" in l]
    g = collections.Counter(re.sub(r"_\d+(_[A-Z]+)?$", "", k.replace("NAV_TTS_TEXT_", "")).split("_")[0] for k in tts)
    out["tts_keys"] = {"count": len(tts), "groups": g.most_common(40), "all": tts}

    # 4) Lua map skin: top-level sections and palette ------------------------------------------------
    st = z.read("assets/res/skins/default/skin_structure.main.lua").decode("utf-8", "replace")
    sec0 = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\{", st, re.M)
    sec1 = re.findall(r"^\t([A-Za-z_][A-Za-z0-9_]*)\s*=?\s*\{", st, re.M)
    out["skin_structure"] = {"lines": st.count("\n"), "top_sections": sec0[:80], "second_level_names": sorted(set(sec1))[:150],
                             "calls_to_functions": collections.Counter(re.findall(r"\b([A-Z][A-Za-z]+)\s*\(", st)).most_common(25)}
    palettes = {}
    for mode in ("day", "night"):
        t = z.read(f"assets/res/skins/default/skin_values.{mode}.lua").decode("utf-8", "replace")
        pal = re.findall(r"^\s*([a-z_][a-z0-9_]*)\s*=\s*rgba?\(0x([0-9A-Fa-f]{6,8})\)", t, re.M)
        palettes[mode] = {"colors": len(pal), "lines": t.count("\n"), "sample": pal[:60]}
    out["skin_palette"] = palettes

    # 5) drawable/mipmap name families (non-library) --------------------------------------------------
    lib = re.compile(r"^(abc_|mtrl_|m3_|design_|material_|common_google|googleg|ic_mtrl|notification_|exo_|ic_call|btn_|test_|tooltip_|navigation_empty|avd_|\$)")
    fam = collections.Counter()
    ext = collections.Counter()
    import csv
    for row in csv.DictReader(open(res_files_csv)):
        if row["type"] in ("drawable", "mipmap") and not lib.match(row["name"]):
            fam[row["name"].split("_")[0]] += 1
            ext[os.path.splitext(row["path"])[1]] += 1
    out["drawable_families_first_party"] = {"total": sum(fam.values()), "by_ext": ext.most_common(), "top": fam.most_common(60)}

    # 6) preserved first-party class vocabulary -------------------------------------------------------
    byp = collections.defaultdict(list)
    for name in open(names_txt).read().splitlines():
        segs = name.split(".")
        simple = segs[-1].split("$")[0]
        if len(simple) >= 5 and not re.fullmatch(r"[a-z]{1,3}\d*", simple):
            byp[".".join(segs[:-1])].append(simple)
    vocab = {}
    for pkg in ("com.waze.car_lib.screens", "com.waze.reports_v2.presentation", "com.waze.search.v2", "com.waze.settings.tree", "com.waze.copilot.data",
                "com.waze.trip_overview", "com.waze.app_nav.hub", "com.waze.uid.activities", "com.waze.planned_drive", "com.waze.sdk", "com.waze.asks",
                "com.waze.map.canvas", "com.waze.navigate", "com.waze.sound", "com.waze.view.popups", "com.waze.authentication", "com.waze.network",
                "com.waze.location", "com.waze.config", "com.waze.modules.navigation", "com.waze.stats", "com.waze.jni.protos"):
        names = sorted(set(byp.get(pkg, [])))
        vocab[pkg] = {"preserved_names": len(names), "sample": names[:40]}
    out["class_vocabulary"] = vocab
    protos = collections.Counter()
    for name in open(names_txt).read().splitlines():
        if name.startswith("com.waze.jni.protos."):
            segs = name.split(".")
            protos[segs[4] if len(segs) > 5 else "(root)"] += 1
    out["jni_protos_by_domain"] = protos.most_common(60)
    car = collections.Counter()
    for name in open(names_txt).read().splitlines():
        if name.startswith("com.waze.car_lib"):
            segs = name.split(".")
            car[segs[3] if len(segs) > 4 else "(root)"] += 1
    out["car_lib_subpackages"] = car.most_common(40)
    json.dump(out, open(os.path.join(out_dir, "features.json"), "w"), indent=1)
    print("settings ids", len(settings), "| lang keys", len(keys), "| tts keys", len(tts), "| skin sections", len(sec0), "| drawable first-party", out["drawable_families_first_party"]["total"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
