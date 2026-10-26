#!/usr/bin/env python3
"""Harness wrapper for the REA (Reverse Engineer Anything) CLI, morluto/rea.

Runs exactly ONE static-analysis `rea` command per call, without a shell.

Input (argv[1]) is either a JSON object
    {"command": "inspect-android-package", "args": ["/abs/app.apk"],
     "timeout": 900, "heap_mib": 600}
or a plain string
    inspect-android-package /abs/app.apk

Only static-analysis commands are accepted. Anything that launches or
instruments a target, attaches to a device or process, or installs packages is
refused here on purpose (the upstream CLI has such commands; this wrapper does
not expose them).

The full stdout/stderr of every run is saved under
/workspace/rea-artifacts/skill-runs/ and only a bounded preview is printed.
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time

MAX_PRINT = 60_000
RUNS_DIR = pathlib.Path("/workspace/rea-artifacts/skill-runs")
JADX_JAR = pathlib.Path("/workspace/.rea-tools/jadx-headless-mcp-0.7.1-all.jar")

# Static-analysis families only.
ALLOW = re.compile(
    r"^(analyze|inspect|decompile|function|instructions|compare|capabilities|doctor"
    r"|decode|search|trace|identify|project|evidence|extract-artifact)(-[a-z0-9]+)*$"
)
# Never expose these even if a name happens to match the allow list.
DENY = re.compile(
    r"adb|frida|capture|observe|debug|instrument|install|pull|cutter|rizin|launch"
    r"|record|electron-scenario|browser|web-page|web-network|export-web",
    re.I,
)


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_request(raw):
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"argument is not valid JSON: {exc}")
        command = spec.get("command")
        args = spec.get("args") or []
        if isinstance(args, str):
            args = shlex.split(args)
        return command, [str(a) for a in args], spec
    parts = shlex.split(raw)
    if not parts:
        fail("empty request; pass e.g. 'inspect-android-package /abs/app.apk'")
    return parts[0], parts[1:], {}


def mem_available_mib():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 512


def build_env(spec):
    env = dict(os.environ)
    if "REA_JADX_MCP_JAR" not in env and JADX_JAR.exists():
        env["REA_JADX_MCP_JAR"] = str(JADX_JAR)
    if "REA_JADX_HEAP_MIB" not in env:
        heap = spec.get("heap_mib")
        if not heap:
            heap = max(256, min(int(mem_available_mib() * 0.6), 6144))
        env["REA_JADX_HEAP_MIB"] = str(int(heap))
    apktool = pathlib.Path("/workspace/.boxcompute/tools/apktool/apktool")
    if "REA_APKTOOL_COMMAND" not in env and apktool.exists():
        env["REA_APKTOOL_COMMAND"] = str(apktool)
    return env


def main():
    if len(sys.argv) < 2:
        fail("expected a command, e.g. 'inspect-android-package /abs/app.apk'")
    command, args, spec = parse_request(sys.argv[1])
    if not command or not ALLOW.match(command) or DENY.search(command):
        fail(
            f"command {command!r} is not allowed through this wrapper "
            "(static-analysis commands only)."
        )
    for a in args:
        if DENY.search(a) and a.startswith("-") is False and command.startswith("capture"):
            fail("refused")
    timeout = int(spec.get("timeout") or 900)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = RUNS_DIR / f"{stamp}-{command}.txt"
    cmd = ["rea", command, *args]
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            env=build_env(spec),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = f"timed out after {timeout}s"
        code = 124
    except FileNotFoundError:
        fail("the `rea` CLI is not on PATH (npm i -g rea-agents)", 127)
    elapsed = time.time() - started
    out_path.write_text(
        f"$ {shlex.join(cmd)}\n# exit={code} elapsed={elapsed:.1f}s\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n"
    )
    preview = stdout if len(stdout) <= MAX_PRINT else stdout[:MAX_PRINT] + "\n[...truncated...]"
    print(preview)
    if stderr.strip():
        print("--- stderr ---", file=sys.stderr)
        print(stderr[-4000:], file=sys.stderr)
    print(f"\n[rea exit={code} elapsed={elapsed:.1f}s full output: {out_path}]", file=sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    main()
