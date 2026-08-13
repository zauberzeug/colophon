---
name: colophon
description: Builds the Colophon sigil `※` — a link at the end of a line that declares AI co-authorship — for Jira, Slack, GitHub and Trello, plus an HTML anchor for mail and wiki pages and a label+URL pair for callers that build the link themselves. Use it whenever a comment, ticket, PR description, issue, e-mail or message is written and the AI contributed substantially, even without an explicit request to mark it. Never write the character by hand — let scripts/sigil.py attach it to your message (--body-file) or paste its output verbatim. Not for git commits (those use the Assisted-by trailer).
---

# Colophon

A sigil `※` at the end of a contribution declares that the text was written with AI support.
It is a link to a static page that names the model and the division of labour.
This skill decides **whether** to mark, writes the free text, and calls `scripts/sigil.py` for the platform link syntax.

## When to mark, when not to

Mark **from** the point where the AI phrased the text or contributed to its substance.

Do not mark for:

- spelling and grammar fixes
- translating individual terms
- autocomplete and mechanical reformatting

Otherwise every contribution carries a sigil and the character becomes meaningless.
When in doubt, mark: a superfluous sigil does little damage, a missing one does more.

Do **not** use it in git commit messages.
Commits keep the trailer `Assisted-by: Claude:claude-opus-5`; `Signed-off-by` always stays with the human.
The sigil is for prose in tickets and chat, the trailer is for commits — different readers, different places.

**Rule:** exactly one sigil per contribution, at the end of the text, after the final punctuation, separated by a normal space.
Not per paragraph — that would be noise.

## How to write the free text

One or two sentences, concrete, in the language of the contribution it is attached to — English if in doubt.
It answers exactly one question: **what did the AI contribute, and what did the human?**
The model is already in `--model`, and who stands behind the text follows from who approved it.

The most valuable part of the sentence is the one that names the **division of labour**.
"Substance from the human, form from the model" and "all of it from the model" are entirely different contributions, and that is precisely what you cannot see in the finished text.

Good:

> Substance from the conversation, wording and structure from the model.

> Author's bullet points, written out by the model; figures taken from the linked measurement series.

> Assembled by the agent on its own from the ticket history.

Bad:

> Created with AI support. *(says nothing the sigil does not already say)*

> This text was produced in an iterative process using advanced language models … *(prose fog)*

> Fully reviewed by the author. *(the agent cannot know this)*

### Honesty rule

The free text describes the *actual* share.
If the human supplied the substance, say so.
No flattering, but no downplaying either.

### No claims about review

The agent does not know whether a human has checked the text for correctness — the colophon is written into the draft, so whatever anyone reads already carries the claim.
Sentences like "reviewed by the author" or "unreviewed" therefore do **not** belong in the free text, neither affirming nor denying.
Approval to publish is a different fact and has its own place — the `--unapproved` flag below; it stays out of the free text too.

## `--unapproved` when nobody gave the go

The flag states: no human approved this text before it went out.

- A human read the text (or its draft) and gave an explicit go for it → leave the flag off, even when the agent then posts it via API.
- The text goes out without anyone having read it — standing authorization ("post whatever you find"), a cron job, an autonomous workflow → set the flag.
- In doubt → set the flag: leaving it off is the claim that needs the evidence.

The go must cover the text as posted; if the text changes after the approval beyond typos and formatting, the approval is spent and the flag comes back.
This is a fact about the conversation, not a judgement about the text: either someone said yes to what is going out, or nobody did — and where that is not clear, the last rule settles it.

The former name `--self-posted` still works, but it names the wrong rule: who pressed send does not decide the flag, the missing go does.

## Model identifier

Take it from the running context, lowercase with hyphens, e.g. `claude-opus-5`.
When unsure — after a model switch mid-session, say — prefer coarse (`claude`) over falsely precise.
A wrong model name is worse than an imprecise one.

## Calling the script

Do not build the encoding or the link dialects by hand — always call the script.

For the four platforms, prefer handing it the whole message: `--body-file` reads your text from a file (`-` reads stdin) and prints it back with the mark attached — after the final punctuation, separated by a space.
The character never passes through your hands, so it cannot be dropped or damaged on the way.

```bash
python3 scripts/sigil.py --platform github --model claude-opus-5 \
  --text "Wording from the model, substance from the author." \
  --body-file draft.md
```

Without `--body-file` the script prints exactly one line: for the four platforms the finished sigil — paste it verbatim at the end of your text.
The three remaining targets are not platforms and are not pasted into a text box:
`html` emits markup for a body that stores markup, `json` prints label and href as separate fields for callers that build the link themselves, and `url` prints the bare address alone.
None of them takes `--body-file` — they hand over pieces for you to place.
Pick by what the target stores, not by what it is called — see the sections below.

```bash
python3 scripts/sigil.py --platform <slack|jira|github|trello|html|json|url> \
                         --model <id> \
                         --text "<free text>" \
                         [--body-file <path|->] \
                         [--date YYYY-MM-DD] [--agent <id>] [--tooltip] [--unapproved]
```

### Slack

When posting via the API, set `unfurl_links: false` — otherwise every message drags a preview card of the legend page behind it.

```bash
python3 scripts/sigil.py --platform slack --model claude-opus-5 \
  --text "Drafted by the model from the author's bullet points."
```

```
<https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Drafted%20by%20the%20model%20from%20the%20author%27s%20bullet%20points.|※>
```

### Jira

Wiki markup works on Server/DC and is converted by Cloud on paste — when in doubt, use it.
If you build ADF directly, take `--platform json` and copy both fields from its output into the text node and its link mark — see "Building the link yourself" below.

```bash
python3 scripts/sigil.py --platform jira --model claude-opus-5 \
  --text "Assembled by the agent on its own from the ticket history." --unapproved
```

```
[※|https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Assembled%20by%20the%20agent%20…&p=agent]
```

### GitHub

`--tooltip` appends a Markdown link title, which the browser shows as a native tooltip on hover.
A bonus, not a mechanism: there is no hover on mobile.
The click must always work on its own.

```bash
python3 scripts/sigil.py --platform github --model claude-opus-5 \
  --text "Wording from the model, substance from the author." --tooltip
```

```
[※](https://zauberzeug.github.io/colophon/#m=… "claude-opus-5: Wording from the model, substance from the author.")
```

### Trello

Plain Markdown, no tooltip.

```bash
python3 scripts/sigil.py --platform trello --model claude-opus-5 \
  --text "Substance from the conversation, wording and structure from the model."
```

### HTML

An anchor for anything whose body is markup: an HTML mail, a Confluence page, a rendered template.
`--tooltip` adds a `title` attribute, same bonus as on GitHub.

```bash
python3 scripts/sigil.py --platform html --model claude-opus-5 \
  --text "Substance from the author, wording from the model."
```

```
<a href="https://zauberzeug.github.io/colophon/#m=claude-opus-5&amp;t=Substance%20from%20the%20author%2C%20wording%20from%20the%20model.">※</a>
```

**This output is source, not text.**
It belongs where markup is what gets stored — the HTML body of a mail sent via API, a Confluence storage-format page, a template.
In a visual editor that treats what you type as literal text — the Gmail compose window, a rich-text comment box — pasting it shows the angle brackets to the reader instead of a link.
There, use the editor's own insert-link command, copying the text and the address from `--platform json` — both fields, neither from memory.

The `&` between the fragment parameters comes out as `&amp;`.
This is what makes the anchor safe in the strict case: read as XML — Confluence storage format, XHTML — a bare `&` is a parse error that rejects the whole document, and an HTML parser may read one as the start of a character reference.
Escaped, every parser hands the original URL back.

#### In mail

Put the sigil on the signature line, after the sender's name and separated by a space.
On a line of its own it reads as a footnote to the mail rather than a mark on the text.

A plain-text mail cannot carry a link at all, and the bare URL turns one quiet character into three lines of noise.
Leave the sigil off there and say in the text that it was drafted with AI support.

Mark mail that is **work product**: a status report to an external party, a specification, minutes, anything that will be read later without the surrounding conversation.
A short personal reply stays unmarked, as everywhere else.

### Building the link yourself

`--platform json` prints the two fields every link is made of, ready to copy:

```bash
python3 scripts/sigil.py --platform json --model claude-opus-5 \
  --text "Wording from the model, substance from the author."
```

```json
{"label": "※", "href": "https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=…"}
```

Use it when the target keeps label and href in separate fields — Jira ADF, most API payloads, the insert-link dialog of a visual editor.
In ADF the two fields land here:

```json
{"type": "text", "text": "※", "marks": [{"type": "link", "attrs": {"href": "<URL>"}}]}
```

The reader still sees only `※`; the URL sits in the attribute.
Copy **both** values from the output — the label field exists so the character itself never has to come from memory, which is exactly how a naked sigil once went out.

`--platform url` prints the href alone, for a caller that already carries the label.
Either way the URL separates its parameters with raw `&`, which is right for a JSON payload like the ADF above and for a dialog that takes the address as a string.
If you are writing the URL into markup yourself, do not escape it by hand — take `--platform html`, which emits the whole anchor correctly escaped.
Do not cut the URL out of another platform's output either; that output is meant to be pasted verbatim.

## Further options

- `--date 2026-08-10` — ISO date, optional.
- `--agent claude-code` — agent or tool, if the text was not written directly in a chat.
- `--tooltip` applies to `--platform github` and `--platform html` — the two dialects with a native hover title; elsewhere it warns on stderr and the link stays correct.
- Env `COLOPHON_BASE` overrides the base URL (for local testing, say).

## The mark is the link

Two failures put a broken colophon in front of a reader, and neither is visible to the agent that caused it: a sigil **without** a link says nothing, and a link whose **label** is not the literal character (`%E2%80%BB`, or a word) renders as that text instead of the mark.
Only the URL is percent-encoded; everything after `|` in `<url|label>`, or inside `[…]` in `[label](url)`, is display text.

So: never type the character into a link by hand, and never retype the script's output — paste it.
Better still, on the four platforms, let the script attach the mark itself (`--body-file` above): where nothing is carried, nothing is dropped.

```bash
python3 scripts/check.py "Ordered the parts. ※"   # exit 1 + reason on stderr
```

It checks position, not presence: a sigil at the end of a text is a mark and must be a working link; mid-sentence it is a mention and is left alone.
Integrations with their own tool layer call `is_broken_mark` from `scripts/check.py` at whatever assembles their outgoing text.

## Tests

```bash
python3 scripts/test_sigil.py
python3 scripts/test_check.py
```
