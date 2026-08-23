# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal collection of hand-verified command cheat sheets — one markdown file per technology at `<topic>/<topic>.md`. There is no application code, no build, no test suite, and no package manager here. Every `.md` is *generated output* of the `cheatsheet-forge` pipeline, not a file to edit casually (see Manifest below).

The commands in these sheets are field-tested on the user's own machines and clusters. **Never "correct" a command because it looks wrong** — the Ruby sheet documents a deliberately contradictory `sudo gem install … --user-install`, kept because it worked. Flag concerns in prose; do not edit the command.

## The pipeline (cheatsheet-forge plugin)

The plugin lives in a *sibling* repo — `/Users/hismaili/perso/applications/cheatsheet-forge` — referenced from `.claude-plugin/marketplace.json` as `source: "../cheatsheet-forge"`, and cached at `~/.claude/plugins/cache/cheatsheet-forge-local/cheatsheet-forge/<version>/` (this is `${CLAUDE_PLUGIN_ROOT}`). Read that repo's `README.md` for the full contract.

```
_sources/<topic>/*.txt        raw terminal dumps — gitignored, contain real secrets
    │  /cheatsheet-forge:analyze  → analyst
    ▼
_sources/<topic>/commands.yml scrubbed, provenance-tagged; every entry has source_ref
    │  /cheatsheet-forge:write    → writer
    ▼
<topic>/<topic>.md            the committed cheat sheet
    │  /cheatsheet-forge:review   → reviewer (reads raw dumps, never a summary)
    ▼  human gate
site/                         /cheatsheet-forge:publish → Astro+Starlight, local preview only
```

`/cheatsheet-forge:forge <topic>` runs analyze → write → review and stops at the gate. `/cheatsheet-forge:cleanup <topic>` archives dumps after publishing.

## Run `/cheatsheet-forge:init` first

This repo has **no `.cheatsheet-repo.yml`** and no `CHEATSHEET_REPO` in `.claude/settings.local.json`. Every forge command exits 2 until `/cheatsheet-forge:init` has run once. Verify current resolution with:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/forgeconfig.py"    # prints root, layout, topics, profiles
```

Layout here is `nested` (`<topic>/<topic>.md`) and `sources_dir` is `_sources`. `redact.named_entities` in that config is where employer/client names go — they must never be committed to the plugin.

## Non-negotiable rules

- **Source-only.** A command may only appear in a sheet if it traces to a dump line via `source_ref`. Never invent, never fill gaps from general knowledge. `kafka/` is an empty directory with an empty `_sources/` — that is correct; it stays empty until dumps exist.
- **`_sources/` is gitignored and holds unredacted secrets.** Sanitising happens once, at the analyst step. Both `command` and `verbatim` in `commands.yml` must be free of credentials and identity (home paths, usernames, private IPs, internal hosts); specifics like namespaces and versions are parameterised in `command` (`<NAMESPACE>`) and kept real in `verbatim`.
- **Two deterministic `PreToolUse` hooks** (`hooks/guard.py`) block writes, not model instructions: a secret/PII scan and a topic-boundary check (an `oc` command may not land in `vault.md`). Binary→topic ownership comes from the plugin's `tech-profiles/<tech>.yml`, not from the guard.
- `.claude/` and `.claude-plugin/` are gitignored — local plugin wiring is not part of the published repo.

## Manifest — why you usually must not hand-edit a topic file

`_sources/<topic>/.forge-manifest.json` stores a sha256 of the last generated `<topic>.md`. If you edit a sheet directly, its state flips from `generated`/`unmodified` to `modified`, and **the writer then refuses to run** until the analyst ingests the file back into `commands.yml` (as `origin: pre-existing`, with a `source_ref` pointing into the `.md`). Hand-written prose and tables cannot be represented in `commands.yml` and are reported as at-risk rather than silently dropped. To change a sheet, change `commands.yml` and re-run `/cheatsheet-forge:write`.

## Verification commands

```bash
# Validate a topic's commands.yml: schema, source_ref resolves to a real file:line, secret scan
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint-commands.py" <topic>

# Guard-check one file by hand (empty output = allowed, JSON payload = blocked)
python3 -c "import json,sys;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':sys.argv[1],'content':open(sys.argv[1]).read()}}))" <topic>/<topic>.md \
  | python3 "${CLAUDE_PLUGIN_ROOT}/hooks/guard.py"

# Guard + config fixture tests (run from the plugin repo)
python3 /Users/hismaili/perso/applications/cheatsheet-forge/tests/test_guard.py
```

## House style of a topic file

`# <Topic> Cheat Sheet` → sections named for the *problem*, not the tool. Each section opens with one or two sentences of narrative framing the failure the commands answer ("Clusters fail in predictable ways…"), then a fenced `bash` block whose comments say what each command is for. Placeholders are `<UPPER_SNAKE>`. Sheets close with a `## Key Patterns` table of **Symptom → Move**. Destructive commands carry an explicit consequence; uncertain ones carry a bolded **Uncertain —** note explaining why they were left as-is.
