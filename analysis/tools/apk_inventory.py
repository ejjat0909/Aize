#!/usr/bin/env python3
"""Archive-level inventory of an APK from the ZIP central directory (stdlib only; nothing executed)."""
import collections
import csv
import hashlib
import json
import os
import re
import sys
import zipfile


def bucket(name):
    if re.fullmatch(r"classes\d*\.dex", name):
        return "code: dex"
    if name.startswith("lib/"):
        return "native: lib/" + name.split("/")[1]
    if name == "resources.arsc":
        return "resources.arsc (table)"
    if name.startswith("res/"):
        ext = os.path.splitext(name)[1].lower()
        return {".png": "res: png", ".xml": "res: compiled xml", ".json": "res: lottie json", ".webp": "res: webp", ".ttf": "res: fonts", ".otf": "res: fonts", ".mp3": "res: audio"}.get(ext, "res: other")
    if name.startswith("assets/res/godot/"):
        return "assets: godot pck"
    if name.startswith("assets/res/skins/"):
        return "assets: skins (png/obj/lua)"
    if name.startswith("assets/res/sound/"):
        return "assets: sound prompts (mp3)"
    if name.startswith("assets/res/lang") or name.startswith("assets/res/key_value") or name.startswith("assets/res/search_conf") or name.startswith("assets/res/tts"):
        return "assets: language/tts/search config"
    if name.startswith("assets/dexopt/"):
        return "assets: ART baseline profile"
    if name.startswith("assets/"):
        return "assets: other"
    if name.startswith("META-INF/"):
        return "META-INF"
    return "other (root files, schemas, okhttp list)"


def main(apk, out_json, out_csv):
    z = zipfile.ZipFile(apk)
    infos = z.infolist()
    by = collections.OrderedDict()
    for i in infos:
        b = bucket(i.filename)
        e = by.setdefault(b, [0, 0, 0])
        e[0] += 1
        e[1] += i.file_size
        e[2] += i.compress_size
    tot_u = sum(i.file_size for i in infos)
    tot_c = sum(i.compress_size for i in infos)
    stored = sum(1 for i in infos if i.compress_type == 0)
    top = collections.Counter(i.filename.split("/")[0] if "/" in i.filename else "(root)" for i in infos)
    ext = collections.Counter(os.path.splitext(i.filename)[1].lower() or "(none)" for i in infos)
    # duplicate content (by CRC32 + size is a cheap, collision-resistant-enough duplicate hint)
    crc = collections.defaultdict(list)
    for i in infos:
        if i.file_size > 2048:
            crc[(i.CRC, i.file_size)].append(i.filename)
    dups = [v for v in crc.values() if len(v) > 1]
    dup_bytes = sum((len(v) - 1) * z.getinfo(v[0]).file_size for v in dups)
    # case-insensitive path collisions (resource path shortening)
    low = collections.defaultdict(list)
    for i in infos:
        low[i.filename.lower()].append(i.filename)
    collisions = [v for v in low.values() if len(v) > 1]
    res = {"apk_bytes": os.path.getsize(apk), "sha256": hashlib.sha256(open(apk, "rb").read()).hexdigest(), "entries": len(infos),
           "uncompressed_bytes": tot_u, "compressed_bytes": tot_c, "stored_uncompressed_entries": stored,
           "by_bucket": [[k, v[0], v[1], v[2]] for k, v in sorted(by.items(), key=lambda kv: -kv[1][2])],
           "top_level": top.most_common(), "extensions": ext.most_common(25),
           "duplicate_content_groups": len(dups), "duplicate_redundant_bytes": dup_bytes,
           "duplicate_examples": [v[:4] for v in sorted(dups, key=lambda v: -z.getinfo(v[0]).file_size)[:8]],
           "case_insensitive_collisions": len(collisions), "case_collision_examples": collisions[:5]}
    json.dump(res, open(out_json, "w"), indent=1)
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "bytes", "compressed", "method"])
        for i in infos:
            w.writerow([i.filename, i.file_size, i.compress_size, "stored" if i.compress_type == 0 else "deflate"])
    print("entries", len(infos), "uncompressed MB %.1f" % (tot_u / 1e6), "compressed MB %.1f" % (tot_c / 1e6), "dup groups", len(dups), "dup MB %.1f" % (dup_bytes / 1e6), "case collisions", len(collisions))


if __name__ == "__main__":
    main(*sys.argv[1:4])
