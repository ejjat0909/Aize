#!/usr/bin/env python3
"""Per-class structure + call skeleton straight from DEX bytecode (static; not a decompiler).

For each requested class reports: defining dex, superclass, interfaces, fields, methods (flags,
signature) and - per non-native method - the distinct methods invoked, strings loaded and fields
touched, in first-use order. Complements REA's JADX-based tools when those cannot load the whole
APK in a small VM.

usage: dex_class_detail.py APK OUT.json CLASS [CLASS ...]
"""
import json
import re
import struct
import sys
import zipfile

# Dalvik instruction length (16-bit code units) by opcode
LEN = {}
for op in range(256):
    LEN[op] = 1
for op in (0x02, 0x05, 0x08, 0x13, 0x15, 0x16, 0x19, 0x1a, 0x1c, 0x1f, 0x20, 0x22, 0x23, 0x29, 0xfe, 0xff):
    LEN[op] = 2
for rng in (range(0x2D, 0x32), range(0x32, 0x38), range(0x38, 0x3E), range(0x44, 0x52), range(0x52, 0x60), range(0x60, 0x6E), range(0x90, 0xB0), range(0xD0, 0xE3)):
    for op in rng:
        LEN[op] = 2
for op in (0x03, 0x06, 0x09, 0x14, 0x17, 0x1b, 0x24, 0x25, 0x26, 0x2A, 0x2B, 0x2C, 0xfc, 0xfd):
    LEN[op] = 3
for rng in (range(0x6E, 0x73), range(0x74, 0x79)):
    for op in rng:
        LEN[op] = 3
LEN[0x18] = 5
LEN[0xfa] = LEN[0xfb] = 4
INVOKE = set(range(0x6E, 0x73)) | set(range(0x74, 0x79)) | {0xfa, 0xfb}
IGETPUT, SGETPUT = set(range(0x52, 0x60)), set(range(0x60, 0x6E))
ACC = [(0x1, "public"), (0x2, "private"), (0x4, "protected"), (0x8, "static"), (0x10, "final"), (0x20, "synchronized"), (0x40, "volatile/bridge"), (0x80, "transient/varargs"), (0x100, "native"), (0x200, "interface"), (0x400, "abstract"), (0x1000, "synthetic")]


def uleb(buf, off):
    r = s = 0
    while True:
        b = buf[off]
        off += 1
        r |= (b & 0x7F) << s
        if b < 0x80:
            return r, off
        s += 7


class Dex:
    def __init__(self, buf, name):
        self.buf, self.name = buf, name
        (self.n_str, self.o_str, self.n_type, self.o_type, self.n_proto, self.o_proto, self.n_field, self.o_field,
         self.n_meth, self.o_meth, self.n_cls, self.o_cls) = struct.unpack_from("<12I", buf, 56)
        self.soffs = struct.unpack_from("<%dI" % self.n_str, buf, self.o_str)
        self.types = struct.unpack_from("<%dI" % self.n_type, buf, self.o_type)
        self._s = {}

    def S(self, i):
        v = self._s.get(i)
        if v is None:
            o = self.soffs[i]
            _, o = uleb(self.buf, o)
            v = self.buf[o:self.buf.find(b"\0", o)].decode("utf-8", "replace")
            self._s[i] = v
        return v

    def T(self, i):
        return self.S(self.types[i])

    def type_list(self, off):
        if not off:
            return []
        n = struct.unpack_from("<I", self.buf, off)[0]
        return [self.T(x) for x in struct.unpack_from("<%dH" % n, self.buf, off + 4)]

    def proto(self, i):
        shorty, ret, params = struct.unpack_from("<III", self.buf, self.o_proto + 12 * i)
        return "(" + ",".join(self.type_list(params)) + ")" + self.T(ret)

    def method(self, i):
        c, p, n = struct.unpack_from("<HHI", self.buf, self.o_meth + 8 * i)
        return f"{self.T(c)}->{self.S(n)}{self.proto(p)}"

    def field(self, i):
        c, t, n = struct.unpack_from("<HHI", self.buf, self.o_field + 8 * i)
        return f"{self.T(c)}->{self.S(n)}:{self.T(t)}"

    def classes(self):
        for i in range(self.n_cls):
            yield i, struct.unpack_from("<8I", self.buf, self.o_cls + 32 * i)


def flags(f):
    return " ".join(n for b, n in ACC if f & b)


def short(desc):
    return desc[1:-1].replace("/", ".") if desc.startswith("L") else desc


def scan_code(dex, code_off):
    buf = dex.buf
    if not code_off:
        return None
    _regs, _ins, _outs, _tries, _dbg, units = struct.unpack_from("<HHHHII", buf, code_off)
    base = code_off + 16
    insns = struct.unpack_from("<%dH" % units, buf, base)
    i = 0
    calls, strings, fields, types = [], [], [], []
    seen_c, seen_s, seen_f, seen_t = set(), set(), set(), set()
    while i < units:
        w = insns[i]
        op = w & 0xFF
        if op == 0x00 and w != 0:
            if w == 0x0100:
                i += insns[i + 1] * 2 + 4
            elif w == 0x0200:
                i += insns[i + 1] * 4 + 2
            elif w == 0x0300:
                width, size = insns[i + 1], insns[i + 2] | (insns[i + 3] << 16)
                i += (size * width + 1) // 2 + 4
            else:
                i += 1
            continue
        n = LEN[op]
        if i + n > units:
            break
        if op in INVOKE:
            k = insns[i + 1]
            if k < dex.n_meth and k not in seen_c:
                seen_c.add(k)
                calls.append(dex.method(k))
        elif op == 0x1A:
            k = insns[i + 1]
            if k < dex.n_str and k not in seen_s:
                seen_s.add(k)
                strings.append(dex.S(k))
        elif op == 0x1B:
            k = insns[i + 1] | (insns[i + 2] << 16)
            if k < dex.n_str and k not in seen_s:
                seen_s.add(k)
                strings.append(dex.S(k))
        elif op in IGETPUT or op in SGETPUT:
            k = insns[i + 1]
            if k < dex.n_field and k not in seen_f:
                seen_f.add(k)
                fields.append(dex.field(k))
        elif op in (0x22, 0x1C, 0x1F, 0x23):
            k = insns[i + 1]
            if k < dex.n_type and k not in seen_t:
                seen_t.add(k)
                types.append(dex.T(k))
        i += n
    return {"registers": _regs, "code_units": units, "calls": calls, "strings": strings, "fields": fields, "types": types}


def class_detail(dex, ci, cd):
    cidx, aflags, sup, ifo, src, _ann, data_off, _sv = cd
    out = {"dex": dex.name, "class": short(dex.T(cidx)), "flags": flags(aflags),
           "super": short(dex.T(sup)) if sup != 0xFFFFFFFF else None, "interfaces": [short(x) for x in dex.type_list(ifo)],
           "source_file": dex.S(src) if src != 0xFFFFFFFF else None, "fields": [], "methods": []}
    if not data_off:
        return out
    buf = dex.buf
    sf, off = uleb(buf, data_off)
    inf, off = uleb(buf, off)
    dm, off = uleb(buf, off)
    vm, off = uleb(buf, off)
    fidx = 0
    for k in range(sf + inf):
        d, off = uleb(buf, off)
        fl, off = uleb(buf, off)
        if k == sf:
            fidx = 0
        fidx += d
        out["fields"].append({"field": dex.field(fidx).split("->", 1)[1], "flags": flags(fl)})
    for count in (dm, vm):
        midx = 0
        for _ in range(count):
            d, off = uleb(buf, off)
            midx += d
            fl, off = uleb(buf, off)
            code, off = uleb(buf, off)
            entry = {"method": dex.method(midx).split("->", 1)[1], "flags": flags(fl)}
            if code:
                entry.update(scan_code(dex, code))
            out["methods"].append(entry)
    return out


def main(apk, out_json, names):
    z = zipfile.ZipFile(apk)
    dexes = sorted((n for n in z.namelist() if re.fullmatch(r"classes\d*\.dex", n)), key=lambda n: int(re.sub(r"\D", "", n) or 1))
    want = {("L" + n.replace(".", "/") + ";"): n for n in names}
    result = {}
    for dn in dexes:
        d = Dex(z.read(dn), dn)
        for ci, cd in d.classes():
            desc = d.T(cd[0])
            if desc in want:
                result[want[desc]] = class_detail(d, ci, cd)
    missing = [n for n in names if n not in result]
    json.dump({"classes": result, "missing": missing}, open(out_json, "w"), indent=1)
    for n, r in result.items():
        nat = sum(1 for m in r["methods"] if "native" in m["flags"])
        print(f"{n}: dex={r['dex']} super={r['super']} ifaces={r['interfaces']} fields={len(r['fields'])} methods={len(r['methods'])} native={nat}")
    if missing:
        print("missing:", missing)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
