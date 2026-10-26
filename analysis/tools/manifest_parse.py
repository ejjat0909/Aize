#!/usr/bin/env python3
"""Decode an APK's binary AndroidManifest.xml into structured JSON (static, no execution).

Secrets policy: meta-data values that look like keys/tokens/ids are replaced with
"<redacted len=N>" so the report never reproduces credentials.
"""
import collections
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import axml  # noqa: E402

SECRETISH_NAME = re.compile(r"key|token|secret|password|client_?id|app_?id|api|dsn|sender", re.I)
SECRETISH_VALUE = re.compile(r"^[A-Za-z0-9_\-:.]{16,}$")


def tree(elements):
    root, stack = None, []
    for depth, tag, attrs in elements:
        node = {"tag": tag, "attrs": attrs, "children": []}
        while len(stack) > depth:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root = node
        stack.append(node)
    return root


def resolve(v, ids):
    if isinstance(v, str) and v.startswith("@0x"):
        return "@" + ids.get(v[1:], v[1:])
    return v


def component(node, ids):
    a = {k: resolve(v, ids) for k, v in node["attrs"].items()}
    out = {"name": a.get("name"), "exported": a.get("exported"), "enabled": a.get("enabled"),
           "permission": a.get("permission"), "process": a.get("process"), "theme": a.get("theme"),
           "launchMode": a.get("launchMode"), "screenOrientation": a.get("screenOrientation"),
           "configChanges": a.get("configChanges"), "windowSoftInputMode": a.get("windowSoftInputMode"),
           "taskAffinity": a.get("taskAffinity"), "foregroundServiceType": a.get("foregroundServiceType"),
           "authorities": a.get("authorities"), "directBootAware": a.get("directBootAware"),
           "resizeableActivity": a.get("resizeableActivity"), "supportsPictureInPicture": a.get("supportsPictureInPicture"),
           "showWhenLocked": a.get("showWhenLocked"), "turnScreenOn": a.get("turnScreenOn")}
    out = {k: v for k, v in out.items() if v is not None}
    filters, meta = [], []
    for ch in node["children"]:
        ca = {k: resolve(v, ids) for k, v in ch["attrs"].items()}
        if ch["tag"] == "intent-filter":
            f = {"actions": [], "categories": [], "data": [], "autoVerify": ca.get("autoVerify")}
            for x in ch["children"]:
                xa = {k: resolve(v, ids) for k, v in x["attrs"].items()}
                if x["tag"] == "action":
                    f["actions"].append(xa.get("name"))
                elif x["tag"] == "category":
                    f["categories"].append(xa.get("name"))
                elif x["tag"] == "data":
                    f["data"].append(xa)
            if f["autoVerify"] is None:
                del f["autoVerify"]
            filters.append(f)
        elif ch["tag"] == "meta-data":
            meta.append(meta_entry(ca))
    if filters:
        out["intentFilters"] = filters
    if meta:
        out["metaData"] = meta
    return out


def meta_entry(a):
    name = a.get("name")
    val = a.get("value", a.get("resource"))
    if val is not None and (SECRETISH_NAME.search(name or "") and SECRETISH_VALUE.match(str(val))):
        val = f"<redacted len={len(str(val))}>"
    return {"name": name, "value": val}


def main(apk, ids_json, out_json):
    ids = json.load(open(ids_json))
    z = zipfile.ZipFile(apk)
    els = axml.parse(z.read("AndroidManifest.xml"))
    root = tree(els)
    ra = {k: resolve(v, ids) for k, v in root["attrs"].items()}
    result = {"manifest": {k: ra.get(k) for k in ("package", "versionCode", "versionName", "compileSdkVersion", "compileSdkVersionCodename", "installLocation")}}
    result["usesPermissions"], result["usesFeatures"], result["definedPermissions"] = [], [], []
    result["usesLibraries"], result["queries"] = [], {"packages": [], "intents": [], "providers": []}
    comps = {"activity": [], "activity-alias": [], "service": [], "receiver": [], "provider": []}
    app_attrs, app_meta = {}, []
    for ch in root["children"]:
        a = {k: resolve(v, ids) for k, v in ch["attrs"].items()}
        t = ch["tag"]
        if t == "uses-sdk":
            result["sdk"] = {"min": a.get("minSdkVersion"), "target": a.get("targetSdkVersion"), "max": a.get("maxSdkVersion")}
        elif t in ("uses-permission", "uses-permission-sdk-23"):
            result["usesPermissions"].append({"name": a.get("name"), **({"maxSdkVersion": a["maxSdkVersion"]} if "maxSdkVersion" in a else {}), **({"usesPermissionFlags": a["usesPermissionFlags"]} if "usesPermissionFlags" in a else {})})
        elif t == "uses-feature":
            result["usesFeatures"].append({"name": a.get("name") or a.get("glEsVersion"), "required": a.get("required", "true")})
        elif t == "permission":
            result["definedPermissions"].append({"name": a.get("name"), "protectionLevel": a.get("protectionLevel")})
        elif t == "queries":
            for q in ch["children"]:
                qa = {k: resolve(v, ids) for k, v in q["attrs"].items()}
                if q["tag"] == "package":
                    result["queries"]["packages"].append(qa.get("name"))
                elif q["tag"] == "intent":
                    result["queries"]["intents"].append([{"tag": x["tag"], **{k: resolve(v, ids) for k, v in x["attrs"].items()}} for x in q["children"]])
                elif q["tag"] == "provider":
                    result["queries"]["providers"].append(qa.get("authorities"))
        elif t == "application":
            app_attrs = {k: v for k, v in a.items() if k in ("name", "label", "icon", "roundIcon", "theme", "allowBackup", "largeHeap", "hardwareAccelerated", "usesCleartextTraffic", "networkSecurityConfig", "extractNativeLibs", "supportsRtl", "requestLegacyExternalStorage", "debuggable", "appComponentFactory", "dataExtractionRules", "fullBackupContent", "localeConfig", "enableOnBackInvokedCallback", "vmSafeMode", "banner")}
            for c in ch["children"]:
                tag = c["tag"]
                if tag in comps:
                    comps[tag].append(component(c, ids))
                elif tag == "meta-data":
                    app_meta.append(meta_entry({k: resolve(v, ids) for k, v in c["attrs"].items()}))
                elif tag == "uses-library":
                    ca = {k: resolve(v, ids) for k, v in c["attrs"].items()}
                    result["usesLibraries"].append({"name": ca.get("name"), "required": ca.get("required", "true")})
    result["application"] = app_attrs
    result["applicationMetaData"] = app_meta
    result["components"] = comps

    # derived views ------------------------------------------------------------------------------
    def schemes(compl):
        s = collections.Counter()
        for c in compl:
            for f in c.get("intentFilters", []):
                for d in f["data"]:
                    if d.get("scheme"):
                        s[d["scheme"]] += 1
        return s

    all_c = [c for lst in comps.values() for c in lst]
    deep = []
    for kind, lst in comps.items():
        for c in lst:
            for f in c.get("intentFilters", []):
                if "android.intent.action.VIEW" in f["actions"] and f["data"]:
                    deep.append({"component": c["name"], "kind": kind, "schemes": sorted({d.get("scheme") for d in f["data"] if d.get("scheme")}),
                                 "hosts": sorted({d.get("host") for d in f["data"] if d.get("host")}),
                                 "paths": sorted({d.get(k) for d in f["data"] for k in ("path", "pathPrefix", "pathPattern") if d.get(k)})[:12],
                                 "autoVerify": f.get("autoVerify")})
    result["derived"] = {
        "counts": {k: len(v) for k, v in comps.items()},
        "exported_true": {k: sum(1 for c in v if c.get("exported") == "true") for k, v in comps.items()},
        "with_intent_filters": sum(1 for c in all_c if c.get("intentFilters")),
        "launchers": [c["name"] for c in comps["activity"] + comps["activity-alias"] if any("android.intent.category.LAUNCHER" in f["categories"] for f in c.get("intentFilters", []))],
        "deep_links": deep,
        "schemes": dict(schemes(all_c)),
        "foreground_service_types": collections.Counter(c.get("foregroundServiceType") for c in comps["service"] if c.get("foregroundServiceType")),
        "orientation": collections.Counter(c.get("screenOrientation") for c in comps["activity"] if c.get("screenOrientation")),
        "launch_modes": collections.Counter(c.get("launchMode") for c in comps["activity"] if c.get("launchMode")),
        "first_party_components": {k: sum(1 for c in v if (c.get("name") or "").startswith("com.waze")) for k, v in comps.items()},
    }
    json.dump(result, open(out_json, "w"), indent=1, default=dict)
    d = result["derived"]
    print("package", result["manifest"], "sdk", result.get("sdk"))
    print("components", d["counts"], "exported", d["exported_true"], "filters", d["with_intent_filters"])
    print("launchers", d["launchers"], "schemes", d["schemes"])
    print("permissions", len(result["usesPermissions"]), "features", len(result["usesFeatures"]), "app_meta", len(app_meta))


if __name__ == "__main__":
    main(*sys.argv[1:4])
