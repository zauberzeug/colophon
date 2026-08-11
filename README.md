# Colophon

A character at the end of a line that signals: this text was written with AI support.
Clicking it explains which model was involved and what it contributed.

```
A ±0.05 mm tolerance on the hole pattern is not enough … ※
```

Works in **GitHub**, **Jira**, **Slack** and **Trello**.
One quiet character is easy to ignore, and one click away if you want the detail — no disclaimer line bloating the text.
The system is a **self-declaration**, and it says so: not an audit log, not a cryptographic proof, not a detector for undeclared AI use.

The name comes from the colophon, the note at the end of a book recording how it was made.
The character itself is a *sigil* — a short mark standing in for something longer.
It certifies nothing, it declares.

## Install

In Claude Code, this repository is its own plugin marketplace:

```
/plugin marketplace add zauberzeug/colophon
/plugin install colophon@colophon
```

Later updates come with `/plugin marketplace update colophon`.
Without plugins, symlink the skill into your personal skills directory instead: `ln -s "$PWD/skills/colophon" ~/.claude/skills/colophon`.

## Use it

Nothing to invoke.
The agent appends the sigil itself whenever it has substantially co-written a comment, ticket or message — no prompting needed, and it decides where the threshold lies.
The rules it follows are in [skills/colophon/SKILL.md](skills/colophon/SKILL.md).

To build a sigil by hand, call the script (Python 3, standard library only):

```bash
$ python3 skills/colophon/scripts/sigil.py --platform slack --model claude-opus-5 \
    --text "Drafted by the model from the author's bullet points."
<https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Drafted%20by%20the%20model%20…|※>
```

The output is one line in the link syntax of the chosen platform, ready to paste.
One sigil per contribution, at the end of the text, after the final punctuation, separated by a space.

In **git commits** the convention remains the `Assisted-by: Claude:claude-opus-5` trailer rather than the sigil — different readers, different places.

## When to mark

Mark from the point where the AI phrased the text or contributed to its substance.
Don't mark spelling fixes, translations of individual terms, or autocomplete — otherwise every contribution carries a sigil and the character means nothing.
When in doubt, mark: a superfluous sigil does little damage, a missing one does more.

The declared text is one or two sentences naming the **division of labour** — "substance from the author, wording from the model" and "all of it from the model" are entirely different contributions, and precisely what the finished text doesn't show.

## Who stands behind it

Posting is the endorsement.
Whoever hits "send" puts their name on top and answers for the content, exactly as with text they typed themselves — nobody signs their own e-mail with "I have read this".
So the page states it as a constant: *whoever published this contribution answers for it.*

The one exception is marked explicitly: if an agent published the contribution itself, via API, nobody approved it before it went out, and the page says so loudly.
This flag is the only value in the whole schema that is determined mechanically rather than asserted — an agent always knows whether it posted itself or handed the text to a human to paste.
For the same reason, claims about review ("checked by the author") never belong in the declared text: the agent writes the colophon before anyone could have read it.

## How it works

The sigil `※` is a link to a static GitHub Page.
Everything it declares lives in the URL itself:

```
https://zauberzeug.github.io/colophon/#m=<model>&t=<free text>
```

| Key | Required | Content |
|---|---|---|
| `m` | yes | model identifier, e.g. `claude-opus-5` |
| `t` | yes | 1–2 sentences: what the AI contributed and what the human did |
| `p` | no | `p=agent` only if the agent published the contribution itself |
| `d` | no | ISO date, e.g. `2026-08-10` |
| `a` | no | agent or tool, e.g. `claude-code` |

No backend, no database, no expiry — the link works as long as the page stands, and even without it the URL stays readable in the raw text.
Unknown parameters are ignored rather than rejected, so the schema can grow.
Called without parameters, the page explains the system instead.

The parameters sit in the **fragment**, the part after `#` that browsers never send to the server: the declared text appears in no access log.
This is a deliberate privacy decision — don't rebuild it on `?`.

## The character

**U+203B REFERENCE MARK** — the Japanese *kome-jirushi*, which has long meant "there is a note on this".
Exactly the semantics needed, and:

- **no emoji variant** — renders as a text character everywhere, never as a coloured pictogram
- **wide font coverage** across macOS, Windows, Linux, iOS, Android
- **unclaimed** in Western usage — unlike `†` (deprecated, death), `∎` (end of proof) or `⌘` (the command key)

One codepoint, no variation selectors, no modifiers.

## Platform notes

| | Link syntax | Hover tooltip |
|---|---|---|
| **GitHub** | `[※](URL "title")` | yes — the Markdown link title, add `--tooltip` |
| **Jira** | `[※\|URL]` wiki markup | no |
| **Slack** | `<URL\|※>` | no |
| **Trello** | `[※](URL)` | don't rely on it |

- **GitHub:** the tooltip is a bonus, not a mechanism — there is no hover on mobile, the click must work on its own.
- **Jira:** wiki markup is converted by Cloud on paste; when building ADF directly, the URL becomes the `href` of a link mark on `※`.
- **Slack:** when posting via API, set `unfurl_links: false`, or every message drags a preview card of this page behind it.

## Development

```bash
python3 skills/colophon/scripts/test_sigil.py   # tests, stdlib only
python3 -m http.server 8000                     # preview the page locally
COLOPHON_BASE=http://localhost:8000/ python3 skills/colophon/scripts/sigil.py …
```

GitHub Pages serves `index.html` from `main`, root — no build step.
The page renders entirely client-side and falls back to its explanation view on missing or broken parameters.

The repository doubles as its own plugin marketplace: `.claude-plugin/marketplace.json` lists this repo (`source: "./"`) as the single plugin, and a plugin loads its skills from `skills/`.
