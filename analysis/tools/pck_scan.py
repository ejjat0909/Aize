#!/usr/bin/env python3
"""Directory scan of a Godot .pck archive (pack format 2/3, Godot 4.x). Nothing is executed.

Reads only the file table (paths / sizes / flags) plus a census of Godot node & resource type
names inside binary scenes. Encrypted packs are reported as such and not read further.
"""
import collections
import csv
import json
import mmap
import os
import re
import struct
import sys

GODOT_TYPES = [
    "Node3D", "Node2D", "Node", "Control", "MeshInstance3D", "MultiMeshInstance3D", "ArrayMesh", "PlaneMesh", "BoxMesh", "QuadMesh", "ImmediateMesh",
    "Camera3D", "DirectionalLight3D", "OmniLight3D", "SpotLight3D", "WorldEnvironment", "Environment", "Sky", "ProceduralSkyMaterial", "PanoramaSkyMaterial",
    "StandardMaterial3D", "ORMMaterial3D", "ShaderMaterial", "Shader", "VisualShader", "GPUParticles3D", "CPUParticles3D", "ParticleProcessMaterial",
    "AnimationPlayer", "AnimationTree", "Animation", "Skeleton3D", "CollisionShape3D", "Area3D", "Path3D", "PathFollow3D", "CSGBox3D", "Sprite3D",
    "Label3D", "Decal", "FogVolume", "ReflectionProbe", "VoxelGI", "LightmapGI", "SubViewport", "Viewport", "CanvasLayer", "TextureRect", "Timer",
    "AudioStreamPlayer3D", "AudioStreamPlayer", "GDScript", "PackedScene", "CompressedTexture2D", "ImageTexture", "GradientTexture1D", "Curve",
    "SphereMesh", "CylinderMesh", "CapsuleMesh", "TubeTrailMesh", "RibbonTrailMesh", "BaseMaterial3D", "Environment", "CameraAttributesPractical",
    "SpringArm3D", "RemoteTransform3D", "MarkerEmpty", "Marker3D", "OccluderInstance3D", "GeometryInstance3D", "VisibleOnScreenNotifier3D",
]


def main(path, out_json, out_csv):
    f = open(path, "rb")
    buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    magic, fmt, vmaj, vmin, vpat = struct.unpack_from("<5I", buf, 0)
    assert magic == 0x43504447, "not a Godot PCK"
    off = 20
    flags, file_base = struct.unpack_from("<IQ", buf, off)
    off += 12
    dir_offset = None
    if fmt >= 3:
        dir_offset = struct.unpack_from("<Q", buf, off)[0]
        off += 8
    off += 64  # reserved[16]
    encrypted_dir = bool(flags & 1)
    entries = []
    if encrypted_dir:
        raise SystemExit("directory is encrypted; not read")
    if dir_offset:
        off = dir_offset
    count = struct.unpack_from("<I", buf, off)[0]
    off += 4
    for _ in range(count):
        plen = struct.unpack_from("<I", buf, off)[0]
        off += 4
        p = buf[off:off + plen].split(b"\0")[0].decode("utf-8", "replace")
        off += plen
        foff, fsize = struct.unpack_from("<QQ", buf, off)
        off += 16
        md5 = buf[off:off + 16].hex()
        off += 16
        fl = struct.unpack_from("<I", buf, off)[0] if fmt >= 2 else 0
        off += 4 if fmt >= 2 else 0
        entries.append({"path": p, "offset": foff, "size": fsize, "md5": md5, "flags": fl})
    ext = collections.Counter(os.path.splitext(e["path"])[1].lower() or "(none)" for e in entries)
    ext_bytes = collections.Counter()
    for e in entries:
        ext_bytes[os.path.splitext(e["path"])[1].lower() or "(none)"] += e["size"]
    top = collections.Counter()
    top_bytes = collections.Counter()
    for e in entries:
        parts = e["path"].replace("res://", "").split("/")
        k = "/".join(parts[:2]) if len(parts) > 2 else (parts[0] if len(parts) > 1 else "(root)")
        top[k] += 1
        top_bytes[k] += e["size"]
    encrypted_files = sum(1 for e in entries if e["flags"] & 1)

    # census of Godot types inside binary scene/resource files
    census, files_with = collections.Counter(), collections.Counter()
    scene_files = [e for e in entries if e["path"].lower().endswith((".scn", ".res", ".tscn", ".tres", ".remap")) and not e["flags"] & 1]
    for e in scene_files:
        s = e["offset"] + (file_base if flags & 2 else 0)
        blob = buf[s:s + e["size"]]
        for t in GODOT_TYPES:
            n = blob.count(t.encode())
            if n:
                census[t] += n
                files_with[t] += 1
    shader_files = [e["path"] for e in entries if e["path"].lower().endswith((".gdshader", ".gdshaderinc", ".shader"))]
    script_files = [e["path"] for e in entries if e["path"].lower().endswith((".gd", ".gdc", ".gde", ".cs"))]
    result = {"file": os.path.basename(path), "bytes": len(buf), "pack_format": fmt, "godot_version": f"{vmaj}.{vmin}.{vpat}", "flags": flags,
              "file_base": file_base, "declared_files": count, "listed_files": len(entries), "encrypted_files": encrypted_files,
              "by_extension": [[k, v, ext_bytes[k]] for k, v in ext.most_common()],
              "by_top_dir": [[k, v, top_bytes[k]] for k, v in top.most_common(40)],
              "scene_like_files": len(scene_files), "godot_type_census": [[t, census[t], files_with[t]] for t, _ in census.most_common(60)],
              "shader_files": len(shader_files), "script_files": len(script_files), "sample_paths": [e["path"] for e in entries[:25]]}
    json.dump(result, open(out_json, "w"), indent=1)
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "size", "flags", "md5"])
        for e in entries:
            w.writerow([e["path"], e["size"], e["flags"], e["md5"]])
    print(json.dumps({k: result[k] for k in ("pack_format", "godot_version", "declared_files", "listed_files", "encrypted_files", "scene_like_files", "shader_files", "script_files")}))
    print("by ext:", result["by_extension"][:12])
    print("types:", result["godot_type_census"][:25])


if __name__ == "__main__":
    main(*sys.argv[1:4])
