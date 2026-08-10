---
name: colophon
description: Builds the Colophon sigil `※` — a link at the end of a line that declares AI co-authorship — for Jira, Slack, GitHub and Trello. Use it whenever a comment, ticket, PR description, issue or message for one of these platforms is written and the AI contributed substantially, even without an explicit request to mark it. Not for git commits (those use the Assisted-by trailer).
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
The model is already in `--model`, and who stands behind the text follows from who posted it.

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

The agent does not know whether a human has read the text — it writes the colophon before anyone could have read it.
Sentences like "reviewed by the author" or "unreviewed" therefore do **not** belong in the free text, neither affirming nor denying.
Who carries responsibility follows from who posted, and the page states it on its own.

## `--self-posted` only when publishing itself

- The agent publishes the contribution **itself** in the same move (via API, from a workflow) → set the flag.
- The agent hands the text to a human to paste → leave it off.

Leaving it off is the safe variant: a missing `p` claims nothing false.
This distinction is the only reliable statement about human backing in the whole system — it must not be guessed.
The agent always knows it without asking: it knows whether it posted itself.

## Model identifier

Take it from the running context, lowercase with hyphens, e.g. `claude-opus-5`.
When unsure — after a model switch mid-session, say — prefer coarse (`claude`) over falsely precise.
A wrong model name is worse than an imprecise one.

## Calling the script

Do not build the encoding or the link dialects by hand — always call the script and paste its output verbatim.
It prints exactly one line to stdout.

```bash
python3 scripts/sigil.py --platform <slack|jira|github|trello> \
                         --model <id> \
                         --text "<free text>" \
                         [--date YYYY-MM-DD] [--agent <id>] [--tooltip] [--self-posted]
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
If you build ADF directly, the same URL string becomes the `href` of a link mark on the text `※`.

```bash
python3 scripts/sigil.py --platform jira --model claude-opus-5 \
  --text "Assembled by the agent on its own from the ticket history." --self-posted
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

## Further options

- `--date 2026-08-10` — ISO date, optional.
- `--agent claude-code` — agent or tool, if the text was not written directly in a chat.
- `--tooltip` only applies to `--platform github`; elsewhere it warns on stderr and the link stays correct.
- Env `COLOPHON_BASE` overrides the base URL (for local testing, say).

## Tests

```bash
python3 scripts/test_sigil.py
```
