#!/usr/bin/env python3
"""APK signing-block facts (static): schemes present + signer certificate fingerprint/validity.

The certificate's personal common name (CN) is deliberately not written to the output.
Requires the `openssl` CLI only to pretty-print the DER certificate subject/validity.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

NAMES = {0x7109871A: "APK Signature Scheme v2", 0xF05368C0: "APK Signature Scheme v3", 0x1B93AD61: "APK Signature Scheme v3.1",
         0x6DFF800D: "Source stamp v2", 0x2B09189E: "Source stamp v1", 0x504B4453: "Dependency info (Play)", 0x42726577: "Verity padding",
         0x71777777: "Play frosting metadata"}


def lp(b, o):
    n = struct.unpack_from("<I", b, o)[0]
    return b[o + 4:o + 4 + n], o + 4 + n


def main(apk, out_json):
    size = os.path.getsize(apk)
    f = open(apk, "rb")
    f.seek(max(0, size - 70000))
    tail = f.read()
    i = tail.rfind(b"PK\x05\x06")
    cd_off = struct.unpack_from("<4sHHHHIIH", tail, i)[6]
    f.seek(cd_off - 24)
    footer = f.read(24)
    if footer[8:] != b"APK Sig Block 42":
        json.dump({"signing_block": None}, open(out_json, "w"))
        print("no APK signing block (v1 only?)")
        return
    blk_size = struct.unpack_from("<Q", footer, 0)[0]
    f.seek(cd_off - blk_size - 8)
    blk = f.read(blk_size + 8)
    pairs, off, found = blk[8:-24], 0, {}
    while off < len(pairs):
        ln = struct.unpack_from("<Q", pairs, off)[0]
        pid = struct.unpack_from("<I", pairs, off + 8)[0]
        found[pid] = pairs[off + 12:off + 8 + ln]
        off += 8 + ln
    certs = {}
    for pid in (0x7109871A, 0xF05368C0):
        if pid in found:
            signers, _ = lp(found[pid], 0)
            o = 0
            while o < len(signers):
                signer, o = lp(signers, o)
                signed, _ = lp(signer, 0)
                _digests, q = lp(signed, 0)
                cs, q = lp(signed, q)
                c = 0
                while c < len(cs):
                    cert, c = lp(cs, c)
                    certs[hashlib.sha256(cert).hexdigest()] = cert
    info = []
    for h, der in certs.items():
        with tempfile.NamedTemporaryFile(suffix=".der", delete=False) as t:
            t.write(der)
        r = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", t.name, "-noout", "-subject", "-issuer", "-dates", "-serial"], capture_output=True, text=True)
        os.unlink(t.name)
        d = dict(line.split("=", 1) for line in r.stdout.strip().splitlines() if "=" in line)
        subj = re.sub(r"CN\s*=\s*[^,]+", "CN=<redacted>", d.get("subject", ""))
        info.append({"sha256": h, "subject": subj, "self_signed": d.get("subject") == d.get("issuer"), "not_before": d.get("notBefore"), "not_after": d.get("notAfter")})
    out = {"signing_block_bytes": blk_size, "entries": [{"id": hex(k), "name": NAMES.get(k, "unknown"), "bytes": len(v)} for k, v in found.items()],
           "schemes": [NAMES[k] for k in found if k in NAMES and "Signature" in NAMES[k]], "certificates": info}
    json.dump(out, open(out_json, "w"), indent=1)
    print(json.dumps(out)[:600])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
