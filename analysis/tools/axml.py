#!/usr/bin/env python3
"""Tiny Android binary-XML (AXML) reader.

Only what the structure report needs: element names and typed attributes, read
straight from the compiled XML chunks. No Android SDK required, nothing is
executed. Format reference: frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h
"""
import struct

RES_STRING_POOL = 0x0001
RES_XML = 0x0003
RES_XML_START_ELEMENT = 0x0102
RES_XML_END_ELEMENT = 0x0103
RES_XML_RESOURCE_MAP = 0x0180

TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_FLOAT = 0x04
TYPE_DIMENSION = 0x05
TYPE_FRACTION = 0x06
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12

_UNITS = ["px", "dp", "sp", "pt", "in", "mm"]


def _read_pool(buf, off):
    (_t, hdr, size, count, _styles, flags, strings_start, _styles_start) = struct.unpack_from(
        "<HHIIIIII", buf, off
    )
    utf8 = bool(flags & 0x100)
    offsets = struct.unpack_from("<%dI" % count, buf, off + hdr)
    base = off + strings_start
    out = []
    for o in offsets:
        p = base + o
        if utf8:
            # u16len/u8len (utf-16 length, then utf-8 length), each 1 or 2 bytes
            n = buf[p]
            p += 2 if n & 0x80 else 1
            n8 = buf[p]
            if n8 & 0x80:
                n8 = ((n8 & 0x7F) << 8) | buf[p + 1]
                p += 2
            else:
                p += 1
            out.append(buf[p : p + n8].decode("utf-8", "replace"))
        else:
            n = struct.unpack_from("<H", buf, p)[0]
            p += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", buf, p)[0]
                p += 2
            out.append(buf[p : p + 2 * n].decode("utf-16le", "replace"))
    return out, size


def _fmt(data_type, data, strings, raw_idx):
    if data_type == TYPE_STRING:
        return strings[data] if data < len(strings) else ""
    if data_type == TYPE_REFERENCE:
        return "@0x%08x" % data
    if data_type == TYPE_INT_BOOLEAN:
        return "true" if data else "false"
    if data_type == TYPE_INT_DEC:
        return str(struct.unpack("<i", struct.pack("<I", data))[0])
    if data_type == TYPE_INT_HEX:
        return "0x%x" % data
    if data_type == TYPE_FLOAT:
        return "%g" % struct.unpack("<f", struct.pack("<I", data))[0]
    if data_type == TYPE_DIMENSION:
        mant = struct.unpack("<i", struct.pack("<I", data & 0xFFFFFF00))[0] >> 8
        radix = (data >> 4) & 0x3
        val = mant / [1, 128, 32768, 8388608][radix]
        return "%g%s" % (val, _UNITS[data & 0xF] if (data & 0xF) < 6 else "?")
    if data_type == TYPE_FRACTION:
        mant = struct.unpack("<i", struct.pack("<I", data & 0xFFFFFF00))[0] >> 8
        radix = (data >> 4) & 0x3
        return "%g%%" % (100 * mant / [1, 128, 32768, 8388608][radix])
    if 0x1C <= data_type <= 0x1F:
        return "#%08x" % data
    if raw_idx != 0xFFFFFFFF and raw_idx < len(strings):
        return strings[raw_idx]
    return "0x%x(type 0x%x)" % (data, data_type)


def parse(buf):
    """Return a list of (depth, tag, {attr: value}) in document order, or None."""
    if len(buf) < 8 or struct.unpack_from("<H", buf, 0)[0] != RES_XML:
        return None
    _t, hdr, total = struct.unpack_from("<HHI", buf, 0)
    off = hdr
    strings = []
    elements = []
    depth = 0
    total = min(total, len(buf))
    while off + 8 <= total:
        ctype, chdr, csize = struct.unpack_from("<HHI", buf, off)
        if csize < 8:
            break
        if ctype == RES_STRING_POOL:
            strings, _ = _read_pool(buf, off)
        elif ctype == RES_XML_START_ELEMENT:
            _ln, _cm, _ns, name_idx, astart, asize, acount, _id, _cls, _sty = struct.unpack_from(
                "<IIIIHHHHHH", buf, off + 8
            )
            attrs = {}
            # attributeStart is relative to the start of the attrExt struct, which begins
            # right after the 16-byte node header (chdr), so the array starts at chdr + astart.
            base = off + chdr + astart
            for i in range(acount):
                ans, aname, araw, _sz, _r0, dtype, ddata = struct.unpack_from(
                    "<IIIHBBI", buf, base + i * asize
                )
                key = strings[aname] if aname < len(strings) else "?"
                attrs[key] = _fmt(dtype, ddata, strings, araw)
            tag = strings[name_idx] if name_idx < len(strings) else "?"
            elements.append((depth, tag, attrs))
            depth += 1
        elif ctype == RES_XML_END_ELEMENT:
            depth -= 1
        off += csize
    return elements


def root_and_tags(buf):
    els = parse(buf)
    if not els:
        return None, []
    return els[0][1], [e[1] for e in els]
