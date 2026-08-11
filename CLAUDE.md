# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Colophon renders the sigil `※` — a link appended to AI co-written comments, tickets and messages that declares which model was involved and what it contributed. The repo ships a Claude Code skill (and doubles as its own plugin marketplace), a Python CLI that emits the link in per-platform syntax, and a static GitHub Pages site that displays the declaration.

## Commands

Python 3 standard library only — no dependencies, no build step, no linter configured.

```bash
python3 skills/colophon/scripts/test_sigil.py                          # all tests
python3 skills/colophon/scripts/test_sigil.py TestEncoding.test_round_trip   # single test (unittest syntax: Class or Class.method)

# preview the page locally, and point the script at it:
python3 -m http.server 8000
COLOPHON_BASE=http://localhost:8000/ python3 skills/colophon/scripts/sigil.py --platform slack --model claude-opus-5 --text "…"
```

## Architecture

Three components with no shared code — their only coupling is the **URL fragment schema**. That schema is the API contract; a change to it touches all three:

1. **`skills/colophon/SKILL.md`** — the policy layer. Tells the agent *when* to mark, how to write the free text (division of labour, honesty rule, no review claims), and when `--self-posted` is allowed. The frontmatter `description` is what triggers the skill automatically.
2. **`skills/colophon/scripts/sigil.py`** — the mechanism. Encodes the parameters into the fragment and wraps the URL in one platform's link dialect. Prints exactly one line to stdout; warnings go to stderr so output stays pipe-safe.
3. **`index.html`** — the display. A single static page, served by GitHub Pages from `main` root, that decodes the fragment client-side. Falls back to its legend view on missing/broken parameters; unknown parameters are ignored so the schema can grow.

### The URL schema

```
https://zauberzeug.github.io/colophon/#m=<model>&t=<text>[&p=agent][&d=<date>][&a=<agent>]
```

Parameters live in the **fragment** (`#`), never the query string — browsers don't send fragments to servers, so the declared text stays out of access logs. This is a deliberate privacy decision; do not rebuild it on `?`.

### Platforms vs. targets in sigil.py

`PLATFORMS` (slack, jira, github, trello) are destinations; `TARGETS` adds two generic dialects: `html` (an XML-safe anchor with `&amp;`-escaped href, for markup bodies) and `url` (the bare URL, for callers that keep href and label in separate fields, e.g. Jira ADF). `TOOLTIP_TARGETS` (github, html) are the two dialects with a native hover title. **Tests derive their coverage from these tuples** — a new target added there is automatically exercised by the loop-based tests. Keep that property when extending.

## Conventions

- The sigil is exactly one codepoint, U+203B, no variation selectors (asserted by a test).
- Git commits in this convention use the `Assisted-by: Claude:<model-id>` trailer, **not** the sigil — the sigil is for prose in tickets and chat.
- `p=agent` (`--self-posted`) is the only mechanically determined value in the schema: set only when the agent publishes the contribution itself via API, never guessed.
- Documentation lives in three places that must stay consistent when behavior changes: `README.md`, `SKILL.md`, and the legend text in `index.html`. The plugin descriptions in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are duplicated by design — keep them in sync too.
- The repo is its own plugin marketplace: `.claude-plugin/marketplace.json` lists this repo (`source: "./"`) as the single plugin, and the plugin loads its skills from `skills/`.
