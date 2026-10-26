#!/usr/bin/env python3
"""Cut a minimal APK (manifest + ONE dex) so REA's JADX provider fits in a small VM.

usage: make_dex_slice.py APK classes6.dex OUT.apk
Cross-dex references stay unresolved in JADX output; that is the price of fitting in ~400 MB.
"""
import sys, zipfile
apk, dex, out = sys.argv[1:4]
z = zipfile.ZipFile(apk)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as o:
    o.writestr("AndroidManifest.xml", z.read("AndroidManifest.xml"))
    o.writestr("classes.dex", z.read(dex))
print("wrote", out)
