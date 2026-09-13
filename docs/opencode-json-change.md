# opencode.json change — dual-runtime (Claude Code + opencode)

## What was changed

**File:** `commands-cheat-sheet/opencode.json:1`

**Before:** no file existed. Claude Code used `.claude-plugin/marketplace.json:7` (`source: "../cheatsheet-forge"` via marketplace `cheatsheet-forge-local`) + `.claude/settings.local.json:3` (`enabledPlugins: {"cheatsheet-forge@cheatsheet-forge-local": true}`).

**After:**

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "../cheatsheet-forge/.opencode/plugin/cheatsheet-forge.ts"
  ]
}
```

Previously created as `["../cheatsheet-forge"]` (directory, mirrors Claude's `source`), then refined to explicit file path `["../cheatsheet-forge/.opencode/plugin/cheatsheet-forge.ts"]` to guarantee opencode resolves the TypeScript entrypoint without relying on directory index resolution.

This mirrors Claude's `source: "../cheatsheet-forge"` — relative to `opencode.json`, it resolves to `/Users/hismaili/perso/applications/cheatsheet-forge` — but opencode requires an explicit `Plugin` export, not a Claude `marketplace.json`.

## What was added in the plugin repo to make it load

To keep **Claude compatibility** (no edits to `.claude-plugin/marketplace.json:10` `source: "./"` or `.claude-plugin/plugin.json` or `hooks/hooks.json:5`), all opencode artifacts are additive under `.opencode/`:

- `cheatsheet-forge/.opencode/plugin/cheatsheet-forge.ts:1` — opencode-native `Plugin` (`export default satisfies Plugin` from `@opencode-ai/plugin@1.14.28`). Returns hooks:
  - `tool.execute.before` — port of `hooks/guard.py:1` (313 lines): governs `Write|Edit|MultiEdit` to `*.md|*.mdx|*.yml` inside `cfg.root` (via `forgeconfig.py` resolution), scans ` ```bash|sh|shell` blocks for 11 `SECRET` regexes (JWT, `AKIA*`, `ghp_*`, `hvs_`, private IP, `/Users/`, `.svc.cluster.local`, etc), skips `SAFE_MARKERS` (`<[A-Z_]>`), throws `Error` to block (opencode) vs `sys.exit(2)` (Claude).
  - `permission.ask` / `shell.env` / `config` — mirrors `guard.unknown_topic` handling and `CHEATSHEET_REPO` injection.
- `cheatsheet-forge/.opencode/package.json:1` — `dependencies: {"@opencode-ai/plugin":"^1.14.28"}`. opencode auto-installs on load; `bun install` validates.

```
cheatsheet-forge/
├── .claude-plugin/marketplace.json  # unchanged, source: "./"
├── .opencode/plugin/cheatsheet-forge.ts  # new
├── .opencode/package.json                # new
└── opencode.json  # optional shim if publishing npm
```

Claude ignores `.opencode/` (unknown dot-dir, `governed` only scans `*.md` inside repo), so `tests/test_guard.py:1` still passes.

## Why file path, not directory

`["../cheatsheet-forge"]` as directory would require that directory to have an `opencode.json` or `package.json` main exporting a `Plugin` — it doesn't (it's a Claude plugin). Explicit `.../.opencode/plugin/cheatsheet-forge.ts` guarantees opencode finds the `export default` without npm publish. After `npm publish @hismaili/opencode-cheatsheet-forge`, consumers can switch to `["@hismaili/opencode-cheatsheet-forge@0.3.0"]` and keep local path for dev.

## How to verify

```bash
cat commands-cheat-sheet/opencode.json
cat cheatsheet-forge/.opencode/plugin/cheatsheet-forge.ts | head -20
cat cheatsheet-forge/.opencode/package.json

# opencode loads once at startup — restart required
opencode --help  # should not throw ConfigInvalidError
# In a repo with .cheatsheet-repo.yml, try Write to git/git.md with ghp_... → blocked in opencode (tool.execute.before throws), same as:
python3 -c "import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'git/git.md','content':'ghp_123456789012345678901234567890123456'}}))" | python3 cheatsheet-forge/hooks/guard.py
```

Restart opencode after saving `opencode.json` or any `.opencode/plugin/*.ts` (config is not hot-reloaded).

## Rollback

```bash
rm commands-cheat-sheet/opencode.json
rm -rf cheatsheet-forge/.opencode
# Claude Code continues via .claude-plugin/marketplace.json local shim
```
