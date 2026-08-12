# AI Agent Guidelines

> **For**: AI assistants (Claude Code, Cursor, GitHub Copilot, Codex, etc.)\
> **About**: what Colophon is and how it works — [README.md](README.md)\
> **Skill rules**: when and how to mark AI co-authorship — [skills/colophon/SKILL.md](skills/colophon/SKILL.md)

Colophon renders the sigil `※` — a link appended to AI co-written comments, tickets and messages that declares which model was involved and what it contributed.
The repo ships a Claude Code skill (and doubles as its own plugin marketplace), a Python CLI that emits the link in per-platform syntax, and a static GitHub Pages site that displays the declaration.

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

Three components share no code.
Their shared contract is the **URL fragment schema** — a change to it touches all three.
`SKILL.md` additionally pins `sigil.py`'s CLI flags and output shape (some examples elide the URL with `…`), so interface changes to the script touch the skill as well.

1. **`skills/colophon/SKILL.md`** — the policy layer.
   Tells the agent *when* to mark, how to write the free text (division of labour, honesty rule, no review claims), and when `--unapproved` may stay off.
   The frontmatter `description` is what triggers the skill automatically.
2. **`skills/colophon/scripts/sigil.py`** — the mechanism.
   Encodes the parameters into the fragment and wraps the URL in one platform's link dialect.
   Prints exactly one line to stdout; warnings go to stderr so output stays pipe-safe.
3. **`index.html`** — the display.
   A single static page, served by GitHub Pages from `main` root, that decodes the fragment client-side.
   Falls back to its legend view on missing/broken parameters; unknown parameters are ignored so the schema can grow.

### The URL schema

```
https://zauberzeug.github.io/colophon/#m=<model>&t=<text>[&p=agent][&d=<date>][&a=<agent>]
```

Parameters live in the **fragment** (`#`), never the query string — browsers don't send fragments to servers, so the declared text stays out of access logs.
This is a deliberate privacy decision; do not rebuild it on `?`.

### Platforms vs. targets in sigil.py

`PLATFORMS` (slack, jira, github, trello) are destinations; `TARGETS` adds two generic targets: the `html` dialect (an XML-safe anchor with `&amp;`-escaped href, for markup bodies) and `url` (no link dialect at all — the bare URL, for callers that keep href and label in separate fields, e.g. Jira ADF).
`TOOLTIP_TARGETS` (github, html) are the two dialects with a native hover title.
**Tests derive their coverage from these tuples** — a new target added there is automatically exercised by the loop-based tests.
Keep that property when extending.

## Pair Programming

Work as a pair programmer, not a silent code generator:

- **Think from first principles**: don't settle for the first solution; question assumptions about the true nature of the problem.
- **Requirements first**: verify requirements before implementing, especially when writing or changing tests.
- **Research before guessing**: search the codebase for similar patterns; check online sources for verification.
- **Discuss before deciding**: when strategy is unclear, present options and trade-offs to the user instead of choosing silently.
- **Challenge assumptions**: if the user states something untrue, correct them directly.

## What to Avoid

- **New dependencies** — stdlib-only is a hard constraint: the script must run anywhere a bare `python3` exists, and the page must stay one self-contained static file.
- **New files** when editing existing ones would suffice — the whole system is deliberately small.
- **Unrelated changes** — every changed line traces to the request; out-of-scope defects and ideas become their own issues or PRs, not diff growth.

## Conventions

- The sigil is exactly one codepoint, U+203B, no variation selectors (asserted by a test).
- The `p=agent` semantics — no human approved this exact text before it went out; a fact about the conversation, set when in doubt — is load-bearing; don't loosen it in `SKILL.md` or `index.html`.
- Write prose one sentence per line (semantic line breaks); match the existing voice — declarative, concrete, no filler.

## Before Claiming a Task Complete

1. `python3 skills/colophon/scripts/test_sigil.py` passes.
2. Documentation stays consistent: `README.md`, `SKILL.md` and the legend text in `index.html` describe the same behavior; the duplicated plugin descriptions in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` match.
3. Review your own diff for unintended scope creep.

## Git & Pull Requests

- Commits with substantial AI contribution carry the `Assisted-by: Claude:<model-id>` trailer — **not** the sigil, which is for prose in tickets and chat.
- Never amend and force-push a PR branch — address review feedback with new commits; amending destroys review context.

---

> Maintainers: update this file as conventions evolve.
