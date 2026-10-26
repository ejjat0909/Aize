# Installing the REA skill

Upstream: <https://github.com/morluto/rea> — "REA: Reverse Engineer Anything" (MIT). The agent skill is `.agents/skills/reverse-engineer-anything/` (`SKILL.md` + six `references/*.md`). It is **instructions only**: installing it does not register REA's MCP server or any analysis engine.

## What was installed for this project (agent harness with a `skills/` directory)

```bash
# 1. CLI (already present: rea-agents 6.7.0). Verify:
rea --version

# 2. Skill files from the checked-out repo (morluto/rea @ 933af60, skill version 44)
SK=/workspace/.boxcomputeagent/skills/reverse-engineer-anything     # the harness' skills directory
mkdir -p "$SK" && cp -r rea/.agents/skills/reverse-engineer-anything/. "$SK"/
cp "$SK/SKILL.md" "$SK/UPSTREAM_SKILL.md"                           # pristine copy for diffing

# 3. Harness additions: `usage:` / `run:` frontmatter keys + the wrapper in this folder
cp analysis/rea-skill/rea_skill.py "$SK"/
#    SKILL.md frontmatter becomes:  name, description, usage, run: python3 $SKILL_DIR/rea_skill.py
```

`rea_skill.py` runs **one static-analysis `rea` command per call, without a shell**, and refuses anything that launches/instruments a target, touches a device or process, installs packages, drives a browser, or exports web scripts (allow-list of command families + deny-list of risky substrings). It saves each run's full output under `rea-artifacts/skill-runs/` and prints a bounded preview. It defaults `REA_JADX_MCP_JAR`, a memory-aware `REA_JADX_HEAP_MIB` (60 % of `MemAvailable`) and `REA_APKTOOL_COMMAND` when those files exist.

## For other agents (Claude Code, Codex, Cursor, Gemini CLI, …)

```bash
npx rea-agents setup --dry-run --json     # review the proposed MCP registration + skill copy
npx rea-agents setup                      # apply after approval, then restart the agent
```

## Providers

| Task | Needs |
|---|---|
| APK inventory (`inspect-artifact`) | nothing (built in) |
| APK classes/methods (`inspect-android-*`) | `REA_JADX_MCP_JAR` (jadx-headless-mcp 0.7.1) + Java 17+; **memory-hungry on big APKs** — see `analysis/README.md` |
| Resource decoding (`decode-android-resources`) | apktool (`REA_APKTOOL_COMMAND`) |
| Native decompilation | Ghidra / IDA / Hopper (not used here) |
| Godot `.pck` | npm 6.7.0 cannot open it; use `analysis/tools/pck_scan.py` (REA `main` documents support) |

Check readiness: `rea doctor` (reports each missing provider with a remediation).
