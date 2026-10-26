#!/usr/bin/env python3
"""Structure of an APK's compiled resources (static, no execution).

Inputs
  - the APK
  - `aapt2 dump resources <apk>` output (resource table: ids, names, configs, values)
Outputs (JSON under OUT)
  - resources_summary.json   counts per type / config / locale, UI-toolkit signals
  - resource_ids.json        0x7fXXXXXX -> "type/name" (used by manifest_parse.py)
  - design_tokens.json       colors, dimens, integers, bools, fonts, styles (names + values)
  - motion.json              anim / animator / interpolator / Lottie facts
  - layouts.json             layout inventory (root tag, element tags, configs)
  - resource_files.csv       res/<short path> -> type, name, config
"""
import collections
import csv
import json
import os
import re
import statistics
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axml  # noqa: E402

RES_RE = re.compile(r"^    resource (0x[0-9a-f]{8}) ([a-z]+)/(\S+)\s*(.*)$")
CFG_RE = re.compile(r"^      \(([^)]*)\) ?(.*)$")
NON_LOCALE = {
    "land", "port", "night", "notnight", "ldrtl", "ldltr", "hdpi", "mdpi", "ldpi", "xhdpi",
    "xxhdpi", "xxxhdpi", "tvdpi", "anydpi", "nodpi", "watch", "car", "tv", "desk", "appliance",
    "small", "normal", "large", "xlarge", "round", "notround", "keysexposed", "keyshidden",
    "nokeys", "qwerty", "12key", "nonav", "dpad", "trackball", "wheel", "touchscreen",
    "notouch", "finger", "stylus", "long", "notlong", "highdr", "lowdr", "widecg", "nowidecg",
    "vrheadset", "square",
}


FW = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "framework_ids.json")))  # from android.jar via javap
FW_ANIM_MS = {"0x010e0000": 200, "0x010e0001": 400, "0x010e0002": 500}  # config_{short,medium,long}AnimTime framework defaults


def dur_ms(v, ids, int_tokens):
    """Duration attribute -> milliseconds (resolving @integer/... and framework config_*AnimTime), or None."""
    if v is None:
        return None
    if isinstance(v, str) and v.startswith("@0x"):
        key = v[1:].lower()
        if key in FW_ANIM_MS:
            return FW_ANIM_MS[key]
        nm = ids.get(key)
        if nm and nm.startswith("integer/"):
            val = int_tokens.get(nm.split("/", 1)[1], {}).get("default")
            try:
                return int(float(val))
            except (TypeError, ValueError):
                return None
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def interp_name(v, ids):
    if not isinstance(v, str) or not v.startswith("@0x"):
        return v
    key = v[1:].lower()
    return (f"android:{FW[key]}" if key in FW else None) or ids.get(key) or v


def parse_dump(path):
    entries, cur, cfg = [], None, None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = RES_RE.match(line)
            if m:
                cur = {"id": m.group(1), "type": m.group(2), "name": m.group(3), "values": []}
                entries.append(cur)
                cfg = None
                continue
            m = CFG_RE.match(line)
            if m and cur is not None:
                cfg = {"config": m.group(1), "value": m.group(2), "extra": []}
                cur["values"].append(cfg)
                continue
            if cfg is not None and line.startswith("        ") and len(cfg["extra"]) < 80:
                cfg["extra"].append(line.strip())
    return entries


def is_locale(config):
    first = config.split("-")[0] if config else ""
    if config.startswith("b+"):
        return True
    return bool(re.fullmatch(r"[a-z]{2,3}", first)) and first not in NON_LOCALE


def file_path(value):
    m = re.match(r"\(file\) (\S+)", value)
    return m.group(1) if m else None


def lottie_facts(raw):
    try:
        d = json.loads(raw)
    except Exception:
        return None
    if not isinstance(d, dict) or "layers" not in d:
        return None
    fr = d.get("fr") or 0
    ip, op = d.get("ip", 0), d.get("op", 0)
    return {
        "v": d.get("v"),
        "fps": fr,
        "frames": op - ip,
        "seconds": round((op - ip) / fr, 2) if fr else None,
        "w": d.get("w"),
        "h": d.get("h"),
        "layers": len(d.get("layers", [])),
        "assets": len(d.get("assets", [])),
        "name": d.get("nm"),
    }


def main(apk, dump, out):
    os.makedirs(out, exist_ok=True)
    entries = parse_dump(dump)
    zf = zipfile.ZipFile(apk)
    zinfo = {i.filename: i for i in zf.infolist()}

    by_type = collections.defaultdict(lambda: {"entries": 0, "values": 0, "files": 0})
    configs = collections.Counter()
    qualifiers = collections.Counter()
    locale_strings = collections.Counter()
    ids, files = {}, []
    for e in entries:
        t = by_type[e["type"]]
        t["entries"] += 1
        ids[e["id"]] = f'{e["type"]}/{e["name"]}'
        for v in e["values"]:
            t["values"] += 1
            cfg = v["config"]
            configs[(e["type"], cfg)] += 1
            for q in filter(None, cfg.split("-")):
                qualifiers[q] += 1
            if e["type"] == "string" and is_locale(cfg):
                locale_strings[cfg] += 1
            p = file_path(v["value"])
            if p:
                t["files"] += 1
                files.append({"path": p, "type": e["type"], "name": e["name"], "config": cfg})

    # -- resource_files.csv + size per resource type -------------------------------------------
    size_by_type = collections.defaultdict(lambda: [0, 0, 0])
    with open(os.path.join(out, "resource_files.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "type", "name", "config", "bytes", "compressed"])
        for f in files:
            zi = zinfo.get(f["path"])
            sz, cz = (zi.file_size, zi.compress_size) if zi else (0, 0)
            w.writerow([f["path"], f["type"], f["name"], f["config"], sz, cz])
            s = size_by_type[f["type"]]
            s[0] += 1
            s[1] += sz
            s[2] += cz

    # -- design tokens (names + values only; no artwork) ---------------------------------------
    tokens = {"color": {}, "dimen": {}, "integer": {}, "bool": {}, "fraction": {}}
    for e in entries:
        if e["type"] in tokens:
            tokens[e["type"]][e["name"]] = {v["config"] or "default": v["value"] for v in e["values"]}
    styles = []
    for e in entries:
        if e["type"] != "style":
            continue
        v0 = e["values"][0] if e["values"] else {"value": "", "extra": []}
        pm = re.search(r"parent=(\S+)", v0["value"])
        sz = re.search(r"size=(\d+)", v0["value"])
        styles.append({"name": e["name"], "parent": pm.group(1) if pm else None,
                       "items": int(sz.group(1)) if sz else 0,
                       "configs": len(e["values"])})
    fonts = []
    for e in entries:
        if e["type"] == "font":
            for v in e["values"]:
                p = file_path(v["value"])
                fonts.append({"name": e["name"], "config": v["config"], "file": p,
                              "ext": os.path.splitext(p)[1] if p else None,
                              "bytes": zinfo[p].file_size if p in zinfo else None})
    json.dump({"tokens": tokens, "styles": styles, "fonts": fonts},
              open(os.path.join(out, "design_tokens.json"), "w"), indent=1)

    # -- walk every XML resource once (layouts, drawables, anims, ...) -------------------------
    layout_tags, layout_roots = collections.Counter(), collections.Counter()
    layouts = []
    drawable_roots, drawable_ext = collections.Counter(), collections.Counter()
    anim, animator, interp, xmlres, transitions = [], [], [], [], []
    compose_layouts = []
    for f in files:
        p = f["path"]
        ext = os.path.splitext(p)[1].lower()
        if f["type"] in ("drawable", "mipmap") and ext != ".xml":
            drawable_ext[ext or "(none)"] += 1
            continue
        if ext != ".xml" or p not in zinfo:
            continue
        try:
            els = axml.parse(zf.read(p))
        except Exception:
            els = None
        if not els:
            continue
        root = els[0]
        t, name = f["type"], f["name"]
        if t == "layout":
            tags = [e[1] for e in els]
            layout_tags.update(tags)
            layout_roots[root[1]] += 1
            layouts.append({"name": name, "config": f["config"], "root": root[1], "elements": len(tags)})
            if any("ComposeView" in x for x in tags):
                compose_layouts.append(name)
        elif t in ("drawable", "mipmap"):
            drawable_roots[root[1]] += 1
        elif t == "anim":
            node_attrs = [root[2]] + [e[2] for e in els[1:]]
            durs = sorted({d for d in (dur_ms(x.get("duration"), ids, tokens["integer"]) for x in node_attrs) if d is not None})
            offs = sorted({d for d in (dur_ms(x.get("startOffset"), ids, tokens["integer"]) for x in node_attrs) if d})
            ips = sorted({interp_name(x.get("interpolator"), ids) for x in node_attrs if x.get("interpolator")})
            anim.append({"name": name, "root": root[1], "children": [e[1] for e in els[1:]][:6], "durations_ms": durs, "start_offsets_ms": offs, "interpolators": ips})
        elif t == "animator":
            node_attrs = [e[2] for e in els]
            durs = sorted({d for d in (dur_ms(x.get("duration"), ids, tokens["integer"]) for x in node_attrs) if d is not None})
            ips = sorted({interp_name(x.get("interpolator"), ids) for x in node_attrs if x.get("interpolator")})
            animator.append({"name": name, "root": root[1], "tags": sorted({e[1] for e in els}),
                             "properties": sorted({e[2].get("propertyName") for e in els if e[2].get("propertyName")}), "durations_ms": durs, "interpolators": ips})
        elif t == "interpolator":
            interp.append({"name": name, "root": root[1], "attrs": root[2]})
        elif t == "xml":
            xmlres.append({"name": name, "root": root[1], "attrs": dict(list(root[2].items())[:6])})
        elif t == "transition":
            transitions.append({"name": name, "root": root[1]})

    # -- Lottie / raw -------------------------------------------------------------------------
    lottie, raw_other = [], []
    for e in entries:
        if e["type"] != "raw":
            continue
        for v in e["values"]:
            p = file_path(v["value"])
            if not p or p not in zinfo:
                continue
            if p.endswith(".json"):
                lf = lottie_facts(zf.read(p))
                lottie.append({"name": e["name"], "bytes": zinfo[p].file_size, **(lf or {"not_lottie": True})})
            else:
                raw_other.append({"name": e["name"], "file": p, "bytes": zinfo[p].file_size})
    # plain JSON under res/ that is not registered as raw (e.g. other lottie)
    registered = {f["path"] for f in files}
    stray_json = [n for n in zinfo if n.startswith("res/") and n.endswith(".json") and n not in registered]

    LIB = re.compile(r"^(abc_|btn_|mtrl_|design_|m3_|linear_indeterminate|fragment_|m3expressive)")
    waze_anim = [x for x in anim if not LIB.match(x["name"])]
    waze_animator = [x for x in animator if not LIB.match(x["name"])]
    hist = collections.Counter(d for x in waze_anim + waze_animator for d in x["durations_ms"] if d > 0)
    int_durations = {k: v for k, v in tokens["integer"].items() if re.search(r"dur|delay|time|anim|ms", k, re.I)}

    json.dump({"anim": anim, "animator": animator, "interpolator": interp, "lottie": lottie,
               "raw_other": raw_other, "stray_json": stray_json, "xml": xmlres,
               "waze_specific_duration_histogram_ms": sorted(hist.items()), "waze_specific_anim_count": len(waze_anim), "waze_specific_animator_count": len(waze_animator),
               "integer_duration_tokens": int_durations},
              open(os.path.join(out, "motion.json"), "w"), indent=1)
    json.dump({"layouts": layouts, "root_tags": layout_roots.most_common(),
               "tag_counts": layout_tags.most_common(150), "compose_view_layouts": compose_layouts},
              open(os.path.join(out, "layouts.json"), "w"), indent=1)
    json.dump(ids, open(os.path.join(out, "resource_ids.json"), "w"))

    loc = sorted(locale_strings.items(), key=lambda kv: -kv[1])
    summary = {
        "types": {k: dict(v, bytes=size_by_type[k][1], compressed=size_by_type[k][2]) for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]["entries"])},
        "distinct_resources": len(entries),
        "top_configs": collections.Counter({f"{t}:{c or 'default'}": n for (t, c), n in configs.items()}).most_common(40),
        "top_qualifiers": qualifiers.most_common(40),
        "string_locales": {"count": len(loc), "per_locale_entries": loc[:12]},
        "drawable_xml_roots": drawable_roots.most_common(),
        "drawable_file_ext": drawable_ext.most_common(),
        "layout_count": len({l["name"] for l in layouts}),
        "layout_files": len(layouts),
        "layout_root_tags": layout_roots.most_common(12),
        "compose_view_layouts": len(compose_layouts),
        "anim_count": len(anim), "animator_count": len(animator), "interpolator_count": len(interp),
        "lottie_count": len(lottie), "font_files": len(fonts),
    }
    json.dump(summary, open(os.path.join(out, "resources_summary.json"), "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("distinct_resources", "layout_count", "layout_files", "compose_view_layouts", "anim_count", "animator_count", "interpolator_count", "lottie_count", "font_files")}))
    print("types:", {k: v["entries"] for k, v in summary["types"].items()})
    print("string locales:", summary["string_locales"]["count"], "top:", summary["string_locales"]["per_locale_entries"][:4])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
