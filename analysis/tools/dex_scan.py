#!/usr/bin/env python3
"""Lightweight, dependency-free DEX structure scanner (static; nothing is executed).

Walks every classes*.dex in an APK and aggregates
  * class / method / field counts and first-party package tree
  * the JNI boundary (methods flagged `native`) per class
  * library fingerprints by package prefix
  * framework-supertype census (Activity, Fragment, ViewModel, protobuf, gRPC ...)
  * string-pool findings: URLs / hosts / URL schemes / gRPC full-method names,
    plus *counts only* of credential-shaped strings (values are never written)

Memory stays small: each dex is read once, classes are aggregated on the fly.
"""
import collections
import json
import re
import struct
import sys
import time
import zipfile

ACC_NATIVE, ACC_ABSTRACT, ACC_INTERFACE, ACC_ENUM, ACC_ANNOTATION, ACC_SYNTHETIC = 0x100, 0x400, 0x200, 0x4000, 0x2000, 0x1000

URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%\-]{4,220}")
SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.\-]{2,30})://")
GRPC_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*\.[A-Z][A-Za-z0-9_]*/[A-Z][A-Za-z0-9_]*$")
HOST_RE = re.compile(r"^(?:[a-z0-9][a-z0-9\-]{0,40}\.){1,5}(?:com|net|org|io|co|me|tv|fm|ly|app|dev|cloud|info|biz|us|uk|de|fr|es|it|nl|br|mx|ca|au|in|jp|kr|cn|ru|il|ai|gl|link|page|so)$")
SECRET_PATTERNS = {
    "google_api_key (AIza…)": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "aws_access_key_id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "jwt_like": re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
    "github_token": re.compile(r"gh[pousr]_[0-9A-Za-z]{30,}"),
    "stripe_live_key": re.compile(r"[sr]k_live_[0-9A-Za-z]{16,}"),
    "firebase_db_url": re.compile(r"https://[a-z0-9\-]+\.firebaseio\.com"),
}

# supertypes worth counting (descriptor form)
SUPERS_OF_INTEREST = [
    "Landroid/app/Activity;", "Landroidx/appcompat/app/AppCompatActivity;", "Landroidx/fragment/app/FragmentActivity;",
    "Landroidx/activity/ComponentActivity;", "Landroidx/fragment/app/Fragment;", "Landroidx/lifecycle/ViewModel;",
    "Landroid/app/Service;", "Landroid/content/BroadcastReceiver;", "Landroid/content/ContentProvider;",
    "Landroid/view/View;", "Landroid/view/ViewGroup;", "Landroid/widget/FrameLayout;", "Landroid/widget/LinearLayout;",
    "Landroid/widget/TextView;", "Landroid/widget/ImageView;", "Landroidx/constraintlayout/widget/ConstraintLayout;",
    "Lcom/google/protobuf/GeneratedMessageLite;", "Lcom/google/protobuf/GeneratedMessageV3;", "Lio/grpc/stub/AbstractStub;",
    "Lio/grpc/stub/AbstractAsyncStub;", "Lio/grpc/stub/AbstractBlockingStub;", "Landroidx/work/ListenableWorker;", "Landroidx/work/Worker;",
    "Landroidx/work/CoroutineWorker;", "Landroidx/room/RoomDatabase;", "Landroid/app/Application;", "Landroidx/car/app/Screen;",
    "Landroidx/car/app/CarAppService;", "Landroidx/car/app/Session;", "Ljava/lang/Enum;", "Lkotlin/coroutines/jvm/internal/ContinuationImpl;",
    "Lkotlin/coroutines/jvm/internal/SuspendLambda;", "Lkotlin/jvm/internal/Lambda;", "Landroidx/compose/runtime/Composer;",
    "Landroid/os/Binder;", "Landroid/os/AsyncTask;", "Landroid/app/Dialog;", "Landroidx/appcompat/app/AppCompatDialog;",
    "Landroid/widget/BaseAdapter;", "Landroidx/recyclerview/widget/RecyclerView$Adapter;", "Landroidx/recyclerview/widget/RecyclerView$ViewHolder;",
]

# library fingerprints: label -> dotted prefix(es)
LIBS = [
    ("Jetpack Compose (runtime/ui/foundation/material)", ("androidx.compose.",)),
    ("Compose-adjacent: activity-compose / navigation-compose", ("androidx.navigation.compose", "androidx.activity.compose")),
    ("AndroidX AppCompat / Fragment / Lifecycle", ("androidx.appcompat.", "androidx.fragment.", "androidx.lifecycle.")),
    ("AndroidX RecyclerView / ConstraintLayout", ("androidx.recyclerview.", "androidx.constraintlayout.")),
    ("Material Components / Material 3 (views)", ("com.google.android.material.",)),
    ("Android Car App Library (Android Auto)", ("androidx.car.app.",)),
    ("Room", ("androidx.room.",)),
    ("WorkManager", ("androidx.work.",)),
    ("DataStore / Datastore-Preferences", ("androidx.datastore.",)),
    ("CameraX", ("androidx.camera.",)),
    ("Media3 / ExoPlayer", ("androidx.media3.", "com.google.android.exoplayer2.")),
    ("Paging", ("androidx.paging.",)),
    ("Kotlin stdlib", ("kotlin.",)),
    ("kotlinx.coroutines", ("kotlinx.coroutines.",)),
    ("kotlinx.serialization", ("kotlinx.serialization.",)),
    ("Protocol Buffers (lite/java)", ("com.google.protobuf.",)),
    ("gRPC", ("io.grpc.",)),
    ("OkHttp / Okio", ("okhttp3.", "okio.")),
    ("Retrofit", ("retrofit2.",)),
    ("Guava", ("com.google.common.",)),
    ("Gson", ("com.google.gson.",)),
    ("Moshi", ("com.squareup.moshi.",)),
    ("Dagger / Hilt", ("dagger.", "hilt_aggregated_deps", "dagger.hilt.")),
    ("Koin", ("org.koin.",)),
    ("Google Ads / AdMob / Ad Manager", ("com.google.android.gms.ads.", "com.google.ads.")),
    ("Google Play services (gms)", ("com.google.android.gms.",)),
    ("Firebase", ("com.google.firebase.",)),
    ("Google Play Core / Integrity / In-app review", ("com.google.android.play.", "com.google.android.finsky.")),
    ("Facebook SDK", ("com.facebook.",)),
    ("Lottie", ("com.airbnb.lottie.",)),
    ("Glide", ("com.bumptech.glide.",)),
    ("Coil", ("coil.", "coil3.")),
    ("Picasso", ("com.squareup.picasso.",)),
    ("Spotify SDK (audio apps)", ("com.spotify.",)),
    ("Braze / Appboy", ("com.braze.", "com.appboy.")),
    ("Branch", ("io.branch.",)),
    ("AppsFlyer / Adjust", ("com.appsflyer.", "com.adjust.")),
    ("Sentry / Bugsnag", ("io.sentry.", "com.bugsnag.")),
    ("Timber / SLF4J", ("timber.log.", "org.slf4j.")),
    ("Apache Commons / HTTP", ("org.apache.",)),
    ("Jsoup / JSON (org.json)", ("org.jsoup.", "org.json.")),
    ("Waze first-party", ("com.waze.",)),
]


def uleb(buf, off):
    r = s = 0
    while True:
        b = buf[off]
        off += 1
        r |= (b & 0x7F) << s
        if b < 0x80:
            return r, off
        s += 7


def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def desc_to_name(d):
    # Lcom/foo/Bar$Baz;  ->  com.foo.Bar$Baz
    if d.startswith("L") and d.endswith(";"):
        return d[1:-1].replace("/", ".")
    return d


def scan_dex(buf, agg, dex_name):
    (string_ids_size, string_ids_off, type_ids_size, type_ids_off, proto_ids_size, proto_ids_off,
     field_ids_size, field_ids_off, method_ids_size, method_ids_off, class_defs_size, class_defs_off) = struct.unpack_from("<12I", buf, 56)
    version = bytes(buf[4:7]).decode("ascii", "replace")
    stat = {"dex": dex_name, "bytes": len(buf), "version": version, "strings": string_ids_size, "types": type_ids_size,
            "protos": proto_ids_size, "fields": field_ids_size, "methods": method_ids_size, "classes": class_defs_size}
    soffs = struct.unpack_from("<%dI" % string_ids_size, buf, string_ids_off)
    cache = {}

    def S(idx):
        v = cache.get(idx)
        if v is None:
            off = soffs[idx]
            _, off = uleb(buf, off)
            end = buf.find(b"\x00", off)
            v = buf[off:end].decode("utf-8", "replace")
            cache[idx] = v
        return v

    type_str = struct.unpack_from("<%dI" % type_ids_size, buf, type_ids_off)

    def type_desc(i):
        return S(type_str[i])

    def method_name(midx):
        # method_id_item: class_idx(u2) proto_idx(u2) name_idx(u4)
        cls, proto, name = struct.unpack_from("<HHI", buf, method_ids_off + 8 * midx)
        return S(name)

    # -- classes ------------------------------------------------------------------------------
    for i in range(class_defs_size):
        cidx, flags, sup_idx, _ifo, _src, _ann, data_off, _sv = struct.unpack_from("<8I", buf, class_defs_off + 32 * i)
        cname = desc_to_name(type_desc(cidx))
        sup = type_desc(sup_idx) if sup_idx != 0xFFFFFFFF else None
        nfields = nmeth = nnative = nabstract = 0
        native_names = []
        if data_off:
            sf, off = uleb(buf, data_off)
            inf, off = uleb(buf, off)
            dm, off = uleb(buf, off)
            vm, off = uleb(buf, off)
            nfields = sf + inf
            for _ in range(nfields):
                _, off = uleb(buf, off)
                _, off = uleb(buf, off)
            for count in (dm, vm):
                midx = 0
                for _ in range(count):
                    d, off = uleb(buf, off)
                    midx += d
                    mflags, off = uleb(buf, off)
                    _code, off = uleb(buf, off)
                    nmeth += 1
                    if mflags & ACC_NATIVE:
                        nnative += 1
                        native_names.append(method_name(midx))
                    if mflags & ACC_ABSTRACT:
                        nabstract += 1
        agg["classes"] += 1
        agg["methods"] += nmeth
        agg["fields"] += nfields
        agg["native_methods"] += nnative
        segs = cname.split(".")
        for depth in (1, 2, 3):
            agg["pkg_depth"][depth]["classes"][".".join(segs[:depth])] += 1
            agg["pkg_depth"][depth]["methods"][".".join(segs[:depth])] += nmeth
        if sup:
            agg["supers"][sup] += 1
        if flags & ACC_INTERFACE:
            agg["interfaces"] += 1
        if flags & ACC_ENUM:
            agg["enums"] += 1
        if flags & ACC_ANNOTATION:
            agg["annotations"] += 1
        base = cname.split("$")[0].rsplit(".", 1)[-1]
        if "ComposableSingletons$" in cname:
            agg["compose_singletons"] += 1
        if cname.endswith("Kt") or "$Companion" in cname or "$WhenMappings" in cname:
            agg["kotlin_markers"] += 1
        if "ExternalSyntheticLambda" in cname or "$$Lambda$" in cname or "-$$Lambda" in cname:
            agg["synthetic_lambdas"] += 1
        if "$$ExternalSyntheticBackport" in cname or "ExternalSyntheticApiModelOutline" in cname:
            agg["desugar_backports"] += 1
        if cname.endswith("Grpc") or "Grpc$" in cname:
            agg["grpc_classes"].append(cname)
        if cname.startswith("com.waze."):
            agg["fp_classes"] += 1
            agg["fp_methods"] += nmeth
            if len(base) <= 2:
                agg["fp_short_names"] += 1
            if len(segs) >= 3:
                key = ".".join(segs[:4]) if len(segs) >= 5 else ".".join(segs[:3])
                e = agg["fp_pkgs"][key]
                e[0] += 1
                e[1] += nmeth
                e[2] += nnative
            if nnative:
                agg["jni"].append({"class": cname, "native": nnative, "methods": native_names[:60]})
            for suffix in ("Activity", "Fragment", "ViewModel", "Repository", "Manager", "NativeManager", "Service", "Receiver", "Worker",
                           "UseCase", "Controller", "Presenter", "Provider", "Factory", "Helper", "Utils", "Dialog", "View", "Adapter", "Screen",
                           "Module", "Interactor", "Mapper", "Client", "Api", "Dao", "Store", "Tracker", "Analytics"):
                if base.endswith(suffix) and len(base) > len(suffix):
                    agg["fp_suffix"][suffix] += 1
                    break
            if len(agg["fp_names"]) < 200000:
                agg["fp_names"].append(cname)
        # library census (first matching label wins for the exact-prefix counts)
        for label, prefixes in LIBS:
            if cname.startswith(prefixes):
                agg["lib_classes"][label] += 1
                agg["lib_methods"][label] += nmeth
                break

    # -- strings ------------------------------------------------------------------------------
    for i in range(string_ids_size):
        s = S(i)
        n = len(s)
        if n < 6:
            continue
        if "://" in s:
            for m in URL_RE.finditer(s):
                agg["urls"][m.group(0)] += 1
            m = SCHEME_RE.match(s)
            if m:
                agg["schemes"][m.group(1)] += 1
        if "/" in s and n < 160 and GRPC_RE.match(s):
            agg["grpc_methods"].add(s)
        if n < 70 and "." in s and HOST_RE.match(s):
            agg["bare_hosts"][s] += 1
        if n >= 20:
            for label, rx in SECRET_PATTERNS.items():
                if rx.search(s):
                    agg["secrets"][label] += 1
    cache.clear()
    return stat


def new_agg():
    return {
        "classes": 0, "methods": 0, "fields": 0, "native_methods": 0, "interfaces": 0, "enums": 0, "annotations": 0,
        "compose_singletons": 0, "kotlin_markers": 0, "synthetic_lambdas": 0, "desugar_backports": 0, "grpc_classes": [],
        "fp_classes": 0, "fp_methods": 0, "fp_short_names": 0, "fp_pkgs": collections.defaultdict(lambda: [0, 0, 0]),
        "fp_suffix": collections.Counter(), "fp_names": [], "jni": [],
        "pkg_depth": {d: {"classes": collections.Counter(), "methods": collections.Counter()} for d in (1, 2, 3)},
        "supers": collections.Counter(), "lib_classes": collections.Counter(), "lib_methods": collections.Counter(),
        "urls": collections.Counter(), "schemes": collections.Counter(), "grpc_methods": set(), "bare_hosts": collections.Counter(),
        "secrets": collections.Counter(),
    }


def main(apk, out_json, names_txt):
    z = zipfile.ZipFile(apk)
    dexes = sorted((n for n in z.namelist() if re.fullmatch(r"classes\d*\.dex", n)),
                   key=lambda n: int(re.sub(r"\D", "", n) or 1))
    agg, stats = new_agg(), []
    t0 = time.time()
    for n in dexes:
        buf = z.read(n)
        stats.append(scan_dex(buf, agg, n))
        print(f"{n}: classes={stats[-1]['classes']} methods={stats[-1]['methods']} strings={stats[-1]['strings']} ({time.time()-t0:.0f}s)", flush=True)
        del buf

    def top(counter, n):
        return [[k, v] for k, v in counter.most_common(n)]

    hosts = collections.Counter()
    for u in agg["urls"]:
        m = re.match(r"https?://([^/:?#]+)", u)
        if m:
            hosts[m.group(1).lower()] += agg["urls"][u]
    pk_set = set(agg["pkg_depth"][2]["classes"]) | set(agg["pkg_depth"][3]["classes"]) | set(agg["pkg_depth"][1]["classes"])
    bare = {h: c for h, c in agg["bare_hosts"].items() if h not in pk_set and not h.startswith(("android.", "java.", "kotlin.", "androidx.", "com.google.android."))}
    out = {
        "dex_files": stats,
        "totals": {k: agg[k] for k in ("classes", "methods", "fields", "native_methods", "interfaces", "enums", "annotations",
                                       "compose_singletons", "kotlin_markers", "synthetic_lambdas", "desugar_backports")},
        "first_party": {"classes": agg["fp_classes"], "methods": agg["fp_methods"], "short_name_classes": agg["fp_short_names"],
                        "packages": sorted(([k, v[0], v[1], v[2]] for k, v in agg["fp_pkgs"].items()), key=lambda r: -r[1]),
                        "suffix_census": top(agg["fp_suffix"], 40)},
        "jni_classes": sorted(agg["jni"], key=lambda r: -r["native"]),
        "package_depth1": top(agg["pkg_depth"][1]["classes"], 40),
        "package_depth2": [[k, c, agg["pkg_depth"][2]["methods"][k]] for k, c in agg["pkg_depth"][2]["classes"].most_common(90)],
        "package_depth3": [[k, c, agg["pkg_depth"][3]["methods"][k]] for k, c in agg["pkg_depth"][3]["classes"].most_common(120)],
        "libraries": sorted(([k, agg["lib_classes"][k], agg["lib_methods"][k]] for k in agg["lib_classes"]), key=lambda r: -r[1]),
        "supertype_census": [[s, agg["supers"][s]] for s in SUPERS_OF_INTEREST if agg["supers"][s]],
        "top_supertypes": top(agg["supers"], 40),
        "grpc_classes": sorted(agg["grpc_classes"])[:400],
        "grpc_method_strings": sorted(agg["grpc_methods"])[:600],
        "grpc_method_string_count": len(agg["grpc_methods"]),
        "url_count": len(agg["urls"]),
        "urls_top_hosts": top(hosts, 150),
        "urls_sample_by_host": {},
        "url_schemes": top(agg["schemes"], 40),
        "bare_hostnames": sorted(bare)[:300],
        "credential_shaped_string_counts": dict(agg["secrets"]),
        "scan_seconds": round(time.time() - t0),
    }
    by_host = collections.defaultdict(list)
    for u in agg["urls"]:
        m = re.match(r"https?://([^/:?#]+)", u)
        if m and len(by_host[m.group(1).lower()]) < 4:
            by_host[m.group(1).lower()].append(re.sub(r"([?&](?:key|token|api_key|apikey|access_token|client_secret)=)[^&]*", r"\1<redacted>", u)[:160])
    out["urls_sample_by_host"] = {h: by_host[h] for h, _ in hosts.most_common(150)}
    json.dump(out, open(out_json, "w"), indent=1)
    with open(names_txt, "w") as fh:
        fh.write("\n".join(agg["fp_names"]))
    print("TOTAL classes=%d methods=%d fields=%d native=%d first_party=%d urls=%d hosts=%d grpc_methods=%d" % (
        agg["classes"], agg["methods"], agg["fields"], agg["native_methods"], agg["fp_classes"], len(agg["urls"]), len(hosts), len(agg["grpc_methods"])))


if __name__ == "__main__":
    main(*sys.argv[1:4])
