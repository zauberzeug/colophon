# Colophon

A character at the end of a line that signals: this text was written with AI support.
Clicking it explains which model was involved and what it contributed.

```
A ±0.05 mm tolerance on the hole pattern is not enough … ※
```

Works in **GitHub**, **Jira**, **Slack** and **Trello**, and as a plain HTML anchor in **e-mail** and wiki pages.
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

Approval is the endorsement.
Whoever releases a text — by hitting "send", or by reading an agent's draft and giving the explicit go — answers for the content, exactly as with text they typed themselves; nobody signs their own e-mail with "I have read this".
So the page states it as a constant: *whoever approved this contribution answers for it.*

The one exception is marked explicitly: if no human approved the exact text before it went out — an agent posting on standing authorization, from a cron job, an autonomous workflow — the page says so loudly.
The flag is a fact about the conversation, not a judgement about the text: an explicit go for this text means no flag, anything less means the flag, and in doubt the flag — leaving it off is the claim that needs the evidence.
Approval releases a text, it does not vouch for it: claims about review ("checked by the author") still never belong in the declared text, because the colophon is written into the draft — whatever anyone reads already carries the claim.

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
| `p` | no | `p=agent` only if no human approved the text before it went out |
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

`--platform` takes four platforms, named after where the text goes, plus two generic targets named after what they emit:

| | Link syntax | Hover tooltip |
|---|---|---|
| **GitHub** | `[※](URL "title")` | yes — the Markdown link title, add `--tooltip` |
| **Jira** | `[※\|URL]` wiki markup | no |
| **Slack** | `<URL\|※>` | no |
| **Trello** | `[※](URL)` | don't rely on it |
| `html` | `<a href="URL" title="…">※</a>` | yes — the `title` attribute, add `--tooltip` |
| `url` | the bare URL, no link | — |

- **GitHub:** the tooltip is a bonus, not a mechanism — there is no hover on mobile, the click must work on its own.
- **Jira:** wiki markup is converted by Cloud on paste; when building ADF directly, ask for `--platform url` and make that URL the `href` of a link mark on `※`.
- **Slack:** when posting via API, set `unfurl_links: false`, or every message drags a preview card of this page behind it.

## The two generic targets

Only four of the six values name a platform.
The other two name a syntax, because that is the only thing that distinguishes them — the same anchor serves an HTML mail, a Confluence page and a rendered template, and calling it `gmail` would have hidden the other two.

### `html` — anywhere the body is markup

```bash
$ python3 skills/colophon/scripts/sigil.py --platform html --model claude-opus-5 \
    --text "Substance from the author, wording from the model."
<a href="https://zauberzeug.github.io/colophon/#m=claude-opus-5&amp;t=Substance%20from%20the%20author…">※</a>
```

The `&` between the fragment parameters comes out as `&amp;`.
That is what makes the anchor safe in the strict case: read as XML — Confluence storage format, XHTML — a bare `&` is a parse error that rejects the whole document, and an HTML parser may take one for the start of a character reference.
Escaped, every parser hands the original URL back.

This output is **source, not text**: it belongs where markup is what gets stored — the HTML body of a mail sent via API, a storage-format page, a template.
Pasting it into a visual editor that treats typing as literal text, such as the Gmail compose window, shows the reader the angle brackets instead of a link; there, use the editor's insert-link command with `※` as the text and `--platform url` for the address.

In **mail**, put the sigil on the signature line, after the sender's name.
A plain-text mail cannot carry a link at all — leave the sigil off and say in the text that it was drafted with AI support.
Mark mail that is work product: a status report, a specification, minutes.
A short personal reply stays unmarked, as everywhere else.

### `url` — when you build the link yourself

Jira comments written as ADF and most API payloads carry the label and the href in separate fields, so wiki or Markdown wrapping has nothing to attach to and would end up as literal characters in the text.
For those, `--platform url` prints the bare URL and nothing else:

```bash
$ python3 skills/colophon/scripts/sigil.py --platform url --model claude-opus-5 \
    --text "Wording from the model, substance from the author."
https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Wording%20from%20the%20model…
```

The label stays `※` — it just moves to wherever the target keeps its link text.
In ADF:

```json
{"type": "text", "text": "※", "marks": [{"type": "link", "attrs": {"href": "<URL>"}}]}
```

The raw `&` is right for a JSON payload and for a dialog that takes the address as a string.
If you are writing the URL into markup instead, don't escape it by hand — take `--platform html`, which emits the whole anchor already escaped.

Build the sigil one of these two ways rather than cutting the URL back out of another platform's output.
That output is meant to be pasted verbatim; a change to its wrapping would break the cut silently.

## Guarding against a broken colophon

A colophon can arrive damaged in two ways, and both are invisible to whoever caused them.
A sigil can be written **without its link** — then it says nothing at all, because the model, the date and the division of labour live on the page behind it.
Or the link can be built correctly and the **label** damaged in transit: the URL half is percent-encoded throughout, and an agent copying the line into a posting script wrote `%E2%80%BB` — the encoded form of the character — where the literal one belongs.
The link still worked; the reader saw nine literal characters.

Nothing in `sigil.py` can prevent either: the damage happens after it has printed the right answer.
The check therefore belongs at the write path — call `is_broken_mark` from `skills/colophon/scripts/check.py` (stdlib only, travels with `sigil.py`) wherever your outgoing text is assembled, or use it as a command:

```bash
python3 skills/colophon/scripts/check.py "Ordered the parts. ※"   # exit 1 + reason on stderr
```

The rule keys on **position, not presence**: only a sigil in trailing position is a mark.
A trailing link in one of `sigil.py`'s shapes must carry the literal `※` as its label — a label that is the percent-encoding is the observed damage, and a link to the legend page labelled anything else has lost its mark the same way; a trailing naked `※` or `%E2%80%BB` is broken too.
The shapes are derived from `sigil.py` itself rather than transcribed, so a new target is guarded automatically.
Mid-sentence the character is a mention — as in this paragraph — and stays untouched, as does a code span holding either form, a line quoted with `>`, and a label field checked with `is_broken_mark(text, label_field=True)` by payloads that keep href and label apart.
The rule's deliberate gaps are pinned in the tests: damage that is not the last thing in the text escapes, a quoted last line is never checked, and a sentence that legitimately ends in the bare character is flagged — a code span avoids that.
A presence check would reject correct writing, which is how a guard earns its way back out of a codebase.

## Development

```bash
python3 skills/colophon/scripts/test_sigil.py   # tests, stdlib only
python3 skills/colophon/scripts/test_check.py   # write-path rule tests
python3 -m http.server 8000                     # preview the page locally
COLOPHON_BASE=http://localhost:8000/ python3 skills/colophon/scripts/sigil.py …
```

GitHub Pages serves `index.html` from `main`, root — no build step.
The page renders entirely client-side and falls back to its explanation view on missing or broken parameters.

The repository doubles as its own plugin marketplace: `.claude-plugin/marketplace.json` lists this repo (`source: "./"`) as the single plugin, and a plugin loads its skills from `skills/`.
