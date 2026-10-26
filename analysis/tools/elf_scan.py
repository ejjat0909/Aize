#!/usr/bin/env python3
"""Static structure scan of an Android native library (ELF64 .so). Nothing is executed.

Reports: ELF sections + sizes, DT_NEEDED, dynamic imports grouped by API family (GLES/EGL/
Vulkan/AAudio/sensors/...), exports (JNI registration style), NDK/compiler notes, embedded
third-party library banners, GLSL shader counts, embedded source-file paths (from __FILE__ /
log macros) and C++ RTTI namespaces. Credential-looking strings are only counted.
"""
import collections
import json
import mmap
import os
import re
import struct
import sys
import time

SEC_T = {0: "NULL", 1: "PROGBITS", 2: "SYMTAB", 3: "STRTAB", 4: "RELA", 5: "HASH", 6: "DYNAMIC", 7: "NOTE", 8: "NOBITS", 9: "REL", 11: "DYNSYM", 14: "INIT_ARRAY", 15: "FINI_ARRAY", 0x6FFFFFF6: "GNU_HASH", 0x6FFFFFFF: "VERSYM", 0x6FFFFFFE: "VERNEED", 0x70000003: "ARM_ATTRIBUTES", 0x6FFF4C00: "ANDROID_RELR?", 0x60000001: "ANDROID_REL?"}
FAMILIES = [
    ("OpenGL ES (gl*)", re.compile(r"^gl[A-Z]")), ("EGL (egl*)", re.compile(r"^egl[A-Z]")), ("Vulkan (vk*)", re.compile(r"^vk[A-Z]")),
    ("AAudio", re.compile(r"^AAudio")), ("OpenSL ES", re.compile(r"^(sl|SL)[A-Z_]")), ("Android sensors (ASensor*)", re.compile(r"^ASensor")),
    ("ANativeWindow / AHardwareBuffer", re.compile(r"^(ANativeWindow|AHardwareBuffer|ASurface)")), ("AMediaCodec / AMediaExtractor", re.compile(r"^AMedia")),
    ("ACamera / AImage", re.compile(r"^(ACamera|AImage)")), ("AAsset / AConfiguration", re.compile(r"^(AAsset|AConfiguration)")),
    ("ALooper / AInputQueue", re.compile(r"^(ALooper|AInput)")), ("android_log", re.compile(r"^__android_log")), ("JNI helpers", re.compile(r"^(JNI_|Java_)")),
    ("pthread", re.compile(r"^pthread_")), ("sockets / DNS", re.compile(r"^(socket|connect|getaddrinfo|freeaddrinfo|send|recv|poll|epoll|select|bind|listen|accept|setsockopt|getsockopt)")),
    ("libm math", re.compile(r"^(sin|cos|tan|atan|atan2|sqrt|pow|exp|log|floor|ceil|fmod|hypot|asin|acos|round|lround)f?$")),
    ("dl (dlopen/dlsym)", re.compile(r"^dl[a-z]+$")), ("zlib", re.compile(r"^(inflate|deflate|crc32|adler32|compress|uncompress|gz)")),
]
BANNERS = {
    "OpenSSL / BoringSSL": rb"(?:OpenSSL|BoringSSL) [0-9][0-9A-Za-z.\- ]{0,20}",
    "libpng": rb"libpng version [0-9.]+", "zlib (deflate)": rb"deflate [0-9.]+ Copyright", "zlib (inflate)": rb"inflate [0-9.]+ Copyright",
    "SQLite": rb"SQLite format 3|sqlite_version\(\)|SQLite version [0-9.]+", "libjpeg(-turbo)": rb"libjpeg-turbo[ 0-9.]*|JPEG parameter struct mismatch",
    "FreeType": rb"FreeType [0-9.]+|FT_Init_FreeType", "HarfBuzz": rb"harfbuzz|HarfBuzz", "ICU": rb"icudt[0-9]+|ICU [0-9.]+",
    "Godot Engine": rb"Godot Engine v[0-9][0-9A-Za-z.\-+ ()]{0,40}", "Lua": rb"Lua [0-9]\.[0-9](?:\.[0-9])?", "Box2D": rb"Box2D",
    "Bullet physics": rb"btDiscreteDynamicsWorld|Bullet Physics", "protobuf (C++)": rb"google/protobuf/[a-z_/]+\.(?:cc|h)|libprotobuf",
    "abseil": rb"absl::|abseil", "gRPC (C++)": rb"grpc-c\+\+/[0-9.]+|grpc\.[a-z_]+\.", "libcurl": rb"libcurl/[0-9.]+", "nghttp2": rb"nghttp2/[0-9.]+",
    "c-ares": rb"c-ares", "Opus": rb"libopus [0-9.]+|opus_encoder", "Ogg/Vorbis": rb"Xiph\.Org libVorbis|OggS", "speex": rb"speex", "WebP": rb"libwebp|WEBP",
    "Brotli": rb"brotli", "zstd": rb"zstd|ZSTD_", "LZ4": rb"LZ4_", "RapidJSON": rb"rapidjson", "nlohmann json": rb"nlohmann", "Skia": rb"SkiaSharp|skia::",
    "ANGLE": rb"ANGLE \(", "spirv/glslang": rb"glslang|SPIR-V|spirv", "meshoptimizer": rb"meshopt", "Recast/Detour nav": rb"dtNavMesh|rcConfig",
    "H3 / S2 geo": rb"h3Index|S2CellId|s2geometry", "Mapbox / MapLibre": rb"mapbox|maplibre", "Valhalla / OSRM": rb"valhalla|osrm",
    "ONNX / TFLite": rb"onnxruntime|tflite|TfLite|tensorflow", "Crashlytics": rb"crashlytics", "Firebase (C++)": rb"firebase::",
}
RX = {
    "url": re.compile(rb"https?://[\x21-\x7e]{4,200}"),
    "srcpath": re.compile(rb"(?:third_party|client|src|waze|google3|external)/[A-Za-z0-9_./+\-]{3,160}\.(?:cc|cpp|c|h|hpp|mm|m|inl|proto|rs)\b"),
    "protofile": re.compile(rb"[A-Za-z0-9_][A-Za-z0-9_./\-]{3,110}\.proto\b"),
    "rtti": re.compile(rb"(?<![A-Za-z0-9_])N(?:[0-9]{1,3}[A-Za-z_][A-Za-z0-9_]{0,60}){1,6}E(?![A-Za-z0-9_])"),
    "glsl_v300": re.compile(rb"#version 300 es"), "glsl_v310": re.compile(rb"#version 310 es"), "glsl_v100": re.compile(rb"precision (?:lowp|mediump|highp) float;"),
    "glsl_v450": re.compile(rb"#version (?:4[0-9]{2}|3[3-9]0)\b"), "glsl_attr": re.compile(rb"\battribute (?:vec|float|mat)"), "glsl_layout": re.compile(rb"layout ?\(location"),
    "secret_aiza": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"), "secret_pem": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def parse_rtti(raw):
    s = raw.decode("ascii", "ignore")
    i, parts = 1, []
    while i < len(s) and s[i] != "E":
        m = re.match(r"\d{1,3}", s[i:])
        if not m:
            return None
        n = int(m.group(0))
        i += len(m.group(0))
        part = s[i:i + n]
        if len(part) != n:
            return None
        parts.append(part)
        i += n
    return parts if i == len(s) - 1 and parts else None


def main(path, out_json):
    t0 = time.time()
    f = open(path, "rb")
    buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    assert buf[:4] == b"\x7fELF" and buf[4] == 2 and buf[5] == 1, "ELF64 little-endian expected"
    (e_type, e_machine, _v, e_entry, e_phoff, e_shoff, _fl, _eh, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", buf, 16)
    machine = {183: "AArch64", 40: "ARM", 62: "x86-64", 3: "x86"}.get(e_machine, str(e_machine))
    secs = []
    for i in range(e_shnum):
        n, t, fl, addr, off, size, link, info, al, es = struct.unpack_from("<IIQQQQIIQQ", buf, e_shoff + i * e_shentsize)
        secs.append({"i": i, "name_off": n, "type": SEC_T.get(t, hex(t)), "flags": fl, "addr": addr, "off": off, "size": size, "link": link, "entsize": es})
    shstr = secs[e_shstrndx]

    def cstr(off):
        end = buf.find(b"\x00", off)
        return buf[off:end].decode("utf-8", "replace")

    for s in secs:
        s["name"] = cstr(shstr["off"] + s["name_off"])
    by_name = {s["name"]: s for s in secs}
    phdrs = []
    for i in range(e_phnum):
        pt, pf, po, pv, pp, pfs, pms, pal = struct.unpack_from("<IIQQQQQQ", buf, e_phoff + i * e_phentsize)
        phdrs.append({"type": {1: "LOAD", 2: "DYNAMIC", 3: "INTERP", 4: "NOTE", 6: "PHDR", 7: "TLS", 0x6474E550: "GNU_EH_FRAME", 0x6474E551: "GNU_STACK", 0x6474E552: "GNU_RELRO"}.get(pt, hex(pt)), "flags": "".join(c for c, b in (("R", 4), ("W", 2), ("X", 1)) if pf & b), "filesz": pfs, "memsz": pms, "align": pal})

    out = {"file": os.path.basename(path), "bytes": len(buf), "machine": machine, "type": {2: "EXEC", 3: "DYN(shared object)"}.get(e_type, e_type),
           "sections": [{k: s[k] for k in ("name", "type", "size")} for s in secs if s["name"]], "program_headers": phdrs}

    # -- dynamic: NEEDED / SONAME ----------------------------------------------------------------
    dyn = by_name.get(".dynamic")
    needed, soname = [], None
    if dyn:
        strtab = secs[dyn["link"]]
        for k in range(dyn["size"] // 16):
            tag, val = struct.unpack_from("<qQ", buf, dyn["off"] + 16 * k)
            if tag == 1:
                needed.append(cstr(strtab["off"] + val))
            elif tag == 14:
                soname = cstr(strtab["off"] + val)
            elif tag == 0:
                break
    out["needed"], out["soname"] = needed, soname

    # -- dynsym: imports/exports -----------------------------------------------------------------
    ds = by_name.get(".dynsym")
    imports, exports = [], []
    if ds:
        dstr = secs[ds["link"]]
        for k in range(1, ds["size"] // 24):
            st_name, st_info, _o, st_shndx, st_value, st_size = struct.unpack_from("<IBBHQQ", buf, ds["off"] + 24 * k)
            nm = cstr(dstr["off"] + st_name)
            (imports if st_shndx == 0 else exports).append(nm)
    fam = collections.OrderedDict()
    for label, rx in FAMILIES:
        hit = [n for n in imports if rx.match(n)]
        if hit:
            fam[label] = {"count": len(hit), "examples": sorted(hit)[:6]}
    out["imports"] = {"count": len(imports), "families": fam}
    out["exports"] = {"count": len(exports), "JNI_OnLoad": "JNI_OnLoad" in exports,
                      "static_JNI_symbols(Java_*)": sum(1 for n in exports if n.startswith("Java_")), "sample": sorted(exports)[:40]}

    # -- notes: NDK / build id / comment ---------------------------------------------------------
    ident = by_name.get(".note.android.ident")
    if ident:
        o = ident["off"]
        namesz, descsz, _t = struct.unpack_from("<III", buf, o)
        desc = buf[o + 12 + ((namesz + 3) & ~3):o + 12 + ((namesz + 3) & ~3) + descsz]
        out["android_ident"] = {"api_level": struct.unpack_from("<I", desc, 0)[0], "ndk_version": desc[4:68].split(b"\0")[0].decode(), "ndk_build": desc[68:132].split(b"\0")[0].decode() if len(desc) >= 132 else None}
    bid = by_name.get(".note.gnu.build-id")
    if bid:
        o = bid["off"]
        namesz, descsz, _t = struct.unpack_from("<III", buf, o)
        out["build_id"] = buf[o + 12 + ((namesz + 3) & ~3):o + 12 + ((namesz + 3) & ~3) + descsz].hex()
    cm = by_name.get(".comment")
    if cm:
        out["comment"] = sorted({x.decode("utf-8", "replace") for x in buf[cm["off"]:cm["off"] + cm["size"]].split(b"\0") if x})[:6]

    # -- string-level scans ----------------------------------------------------------------------
    counts = collections.Counter()
    urls, srcpaths, protos, rtti = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for name, rx in RX.items():
        for m in rx.finditer(buf):
            counts[name] += 1
            g = m.group(0)
            if name == "url" and len(urls) < 20000:
                urls[g.decode("ascii", "ignore")] += 1
            elif name == "srcpath":
                srcpaths[g.decode("ascii", "ignore")] += 1
            elif name == "protofile":
                protos[g.decode("ascii", "ignore")] += 1
            elif name == "rtti":
                p = parse_rtti(g)
                if p:
                    rtti["::".join(p)] += 1
    out["string_scan"] = {"counts": dict(counts)}
    banners = {}
    for label, pat in BANNERS.items():
        ms = list(re.finditer(pat, buf))
        if ms:
            banners[label] = {"hits": len(ms), "example": ms[0].group(0).decode("ascii", "ignore")[:80]}
    out["embedded_library_banners"] = banners
    hosts = collections.Counter()
    for u in urls:
        m = re.match(r"https?://([^/:?#\s\"'<>]+)", u)
        if m:
            hosts[m.group(1).lower()] += 1
    out["urls"] = {"unique": len(urls), "top_hosts": hosts.most_common(80)}

    def top_dirs(paths, depth):
        c = collections.Counter()
        for p in paths:
            c["/".join(p.split("/")[:depth])] += 1
        return c.most_common(60)

    out["source_paths"] = {"unique_files": len(srcpaths), "top_dirs_d4": top_dirs(srcpaths, 4), "top_dirs_d5": top_dirs(srcpaths, 5), "top_dirs_d6": top_dirs(srcpaths, 6),
                           "extensions": collections.Counter(os.path.splitext(p)[1] for p in srcpaths).most_common(), "sample": sorted(srcpaths)[:40]}
    out["proto_files"] = {"unique": len(protos), "top_dirs_d3": top_dirs(protos, 3), "top_dirs_d2": top_dirs(protos, 2), "sample": sorted(protos)[:60]}
    ns1, ns2, ns3 = collections.Counter(), collections.Counter(), collections.Counter()
    for q in rtti:
        p = q.split("::")
        ns1[p[0]] += 1
        if len(p) > 1:
            ns2["::".join(p[:2])] += 1
        if len(p) > 2:
            ns3["::".join(p[:3])] += 1
    out["cpp_rtti"] = {"unique_types": len(rtti), "top_namespaces_d1": ns1.most_common(45), "top_namespaces_d2": ns2.most_common(60), "top_namespaces_d3": ns3.most_common(60)}
    out["scan_seconds"] = round(time.time() - t0)
    json.dump(out, open(out_json, "w"), indent=1)
    big = sorted(out["sections"], key=lambda s: -s["size"])[:8]
    print("OK", path, "sections", len(secs), "needed", needed, "imports", len(imports), "exports", len(exports), "srcpaths", len(srcpaths), "rtti", len(rtti), "protos", len(protos), "urls", len(urls), "t=%ds" % out["scan_seconds"])
    print("biggest sections:", [(s["name"], s["size"]) for s in big])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
