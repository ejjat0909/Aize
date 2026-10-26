#!/usr/bin/env python3
"""Collect REA evidence ids/timings from rea/*.json + rea/batch.log into one small index (no decompiled text)."""
import json, os, re, sys
rea_dir, out = sys.argv[1], sys.argv[2]
def L(n): return json.load(open(os.path.join(rea_dir, n)))
inv = L("apk-inspect-artifact.json")
sub = inv["normalized_result"]["substeps"][0]
man = sub["evidence"]["normalized_result"]["manifest"]
idx = {"rea_cli": "rea-agents 6.7.0", "jadx_engine": "jadx-headless-mcp 0.7.1",
       "apk_inventory": {"evidence_id": inv["evidence_id"], "inventory_evidence_id": sub["evidence_id"], "sha256": inv["subject"]["digest"]["sha256"],
                         "occurrences": man["occurrence_count"], "unique_nodes": man["node_count"], "edges": man["edge_count"],
                         "limitations": inv["limitations"]},
       "methods": {}, "classes": {}, "timings": {}}
files = {"WazeRenderer.l": "jadx-method-WazeRenderer-l", "WazeRenderer.h": "m-WazeRenderer-h", "WazeRenderer.i": "m-WazeRenderer-i",
         "Location.sendUpdateToNativeLayer": "m-Location-sendUpdate", "Location.createNativeLocationJNI": "m-Location-createJni"}
for k, f in files.items():
    d = L(f + ".json"); idx["methods"][k] = d["evidence_id"]
cfiles = {"NativeCanvasRenderer": "c-NativeCanvasRenderer", "NetworkManager": "c-NetworkManager", "MainCanvasDelegatorImpl": "c-MainCanvasDelegator", "FreeMapAppActivity": "c-FreeMapAppActivity", "SoundNativeManager": "c-SoundNativeManager"}
for k, f in cfiles.items():
    d = L(f + ".json"); idx["classes"][k] = d["evidence_id"]
for line in open(os.path.join(rea_dir, "batch.log")):
    m = re.match(r"(\S+) exit=(\d+) ([\d.]+) s, (\d+) KB", line)
    if m: idx["timings"][m.group(1)] = {"exit": int(m.group(2)), "seconds": float(m.group(3)), "peak_rss_kb": int(m.group(4))}
json.dump(idx, open(out, "w"), indent=1)
print(json.dumps({k: (v if not isinstance(v, dict) else list(v)[:3]) for k, v in idx.items()})[:500])
