#!/usr/bin/env python3
"""Build the Colophon sigil as a ready-to-paste link for Slack, Jira, GitHub and Trello.

Prints exactly one line to stdout — or, with `--body-file`, the whole message
with the mark attached. Warnings go to stderr so the output stays usable in a
pipe.

    sigil.py --platform slack --model claude-opus-5 --text "Drafted by the model."
    echo "Ordered the parts." | sigil.py --platform slack --model claude-opus-5 \\
        --text "Drafted by the model." --body-file -

Both observed colophon failures happened while a hand carried the mark from
this script's output into a message. `--body-file` removes the hand-off for
the four platforms: the message goes in, the message with the mark comes out.
The mark rides at the end of the last line — or as its own final paragraph
when that line is block markup that would swallow an inline suffix (a closing
code fence, a quoted line). A message that already ends in a mark is refused:
one sigil per contribution, and a damaged mark wants repair, not a second
mark on top.

Three targets are not platforms: `--platform html` emits an anchor for
anything whose body is markup (an HTML mail, a Confluence page), `--platform
json` prints label and href as separate fields for callers that build the
link themselves (Jira ADF, an API payload that keeps href and label apart),
and `--platform url` prints the bare URL alone.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
from urllib.parse import quote

DEFAULT_BASE = "https://zauberzeug.github.io/colophon/"

SIGIL = "※"  # U+203B REFERENCE MARK

PLATFORMS = ("slack", "jira", "github", "trello")

# None of these is a platform, so they stay out of PLATFORMS and that remains
# the list of destinations whose dialect you cannot guess from the name.
# `html` is a dialect named after its syntax — an HTML mail body is the common
# case, but so is a Confluence page. `json` emits the two fields every link is
# made of, for callers that build one themselves — the label rides along so
# the character never has to come from memory. `url` emits the href alone.
TARGETS = PLATFORMS + ("html", "json", "url")

# Dialects whose output is the finished mark, label included — what gets
# pasted (or attached) at the end of a message. `json` and `url` hand over
# pieces instead, so damage to them is not a mark damaged in a message tail.
MARK_TARGETS = PLATFORMS + ("html",)

# Dialects whose syntax carries a native hover title.
TOOLTIP_TARGETS = ("github", "html")

# Last lines that swallow an inline suffix instead of ending a sentence: text
# after a closing code fence stops the line from closing the fence at all, and
# on a quoted line the mark would join someone else's words. Markdown fences
# and quotes cover slack, github and trello; the Jira dialect adds its block
# closers and bq. quotation. A prefix list, not a markup parser — an indented
# code block (no prefix character) is the named gap.
BLOCK_TAILS = ("```", "~~~", ">", "bq.", "{code}", "{quote}", "{noformat}")


def base_url():
    """Return the base URL, overridable via the COLOPHON_BASE environment variable."""
    return (os.environ.get("COLOPHON_BASE") or DEFAULT_BASE).strip().rstrip("#")


def normalize(text):
    """Collapse newlines and runs of whitespace into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def build_url(model, text, unapproved=False, date=None, agent=None, base=None):
    """Assemble the Colophon URL: everything in the fragment, everything encoded."""
    params = [("m", model), ("t", text)]
    if unapproved:
        params.append(("p", "agent"))
    if date:
        params.append(("d", date))
    if agent:
        params.append(("a", agent))
    fragment = "&".join(
        "%s=%s" % (key, quote(value, safe="")) for key, value in params
    )
    return "%s#%s" % (base or base_url(), fragment)


def escape_markdown_title(text):
    """Escape backslashes and double quotes for a CommonMark link title."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def format_link(platform, url, tooltip=None):
    """Wrap the URL in the link syntax of the target platform."""
    if platform == "url":
        return url
    if platform == "json":
        # ensure_ascii=False keeps the literal character on screen: this line
        # is the copy source for both fields, label included.
        return json.dumps({"label": SIGIL, "href": url}, ensure_ascii=False)
    if platform == "slack":
        return "<%s|%s>" % (url, SIGIL)
    if platform == "jira":
        return "[%s|%s]" % (SIGIL, url)
    if platform == "html":
        # The `&` separating the fragment parameters has to be written `&amp;`:
        # bare, it is a hard parse error wherever the markup is read as XML
        # (Confluence storage format, XHTML mail), and an HTML parser may take
        # it for a character reference. Escaped, every parser hands the
        # original URL back. The tooltip goes through the same escaping: it
        # carries the free text raw, quotes and angle brackets included.
        attrs = 'href="%s"' % html.escape(url, quote=True)
        if tooltip:
            attrs += ' title="%s"' % html.escape(tooltip, quote=True)
        return "<a %s>%s</a>" % (attrs, SIGIL)
    if platform in ("github", "trello"):
        if platform == "github" and tooltip:
            return '[%s](%s "%s")' % (SIGIL, url, escape_markdown_title(tooltip))
        return "[%s](%s)" % (SIGIL, url)
    raise ValueError("unknown platform: %s" % platform)


def tooltip_text(model, text):
    return "%s: %s" % (model, text)


def needs_own_paragraph(body):
    """True if the body's last line would swallow an inline mark."""
    return body.rsplit("\n", 1)[-1].lstrip().startswith(BLOCK_TAILS)


def attach_mark(body, link):
    """Append the mark after the final punctuation, separated by a space —
    or as its own final paragraph when the last line is block markup."""
    return body + ("\n\n" if needs_own_paragraph(body) else " ") + link


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="sigil.py",
        description="Build the Colophon sigil as a ready-to-paste link.",
        epilog="The base URL defaults to %s and can be overridden "
        "with the COLOPHON_BASE environment variable." % DEFAULT_BASE,
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=TARGETS,
        help="link dialect to emit; `html` emits an anchor for markup bodies, "
        "`json` label and href as separate fields for callers that build the "
        "link themselves, `url` the bare URL alone",
    )
    parser.add_argument("--model", required=True, help="model identifier, e.g. claude-opus-5")
    parser.add_argument(
        "--text",
        required=True,
        help="free text, 1-2 sentences: what the AI contributed and what the human did",
    )
    parser.add_argument("--date", help="ISO date, e.g. 2026-08-10")
    parser.add_argument("--agent", help="agent or tool, e.g. claude-code")
    parser.add_argument(
        "--body-file",
        metavar="PATH",
        help="attach the mark to the message in PATH (`-` reads stdin) and "
        "print the whole message; only for the four platforms",
    )
    parser.add_argument(
        "--tooltip",
        action="store_true",
        help="append a hover title; only effective with --platform github or html",
    )
    parser.add_argument(
        # `--self-posted` was the original name, from when the flag asked who
        # made the API call. It now asks whether anyone gave the go, and those
        # two answers differ in the common case — an agent posting an approved
        # text. Kept as an alias so existing callers keep working.
        "--unapproved",
        "--self-posted",
        action="store_true",
        help="set p=agent — only when no human approved the text before it went out",
    )

    args = parser.parse_args(argv)

    if args.body_file is not None and args.platform not in PLATFORMS:
        parser.error(
            "--body-file only works with a platform (%s); html, json and url "
            "hand over pieces for you to place" % ", ".join(PLATFORMS)
        )

    args.model = normalize(args.model)
    args.text = normalize(args.text)
    if not args.model:
        parser.error("--model must not be empty")
    if not args.text:
        parser.error("--text must not be empty")
    if args.agent is not None:
        args.agent = normalize(args.agent)
        if not args.agent:
            parser.error("--agent must not be empty")
    if args.date is not None:
        args.date = normalize(args.date)
        try:
            datetime.date.fromisoformat(args.date)
        except ValueError:
            parser.error("--date expects an ISO date such as 2026-08-10")

    return args


def main(argv=None):
    args = parse_args(argv)

    body = None
    if args.body_file is not None:
        try:
            if args.body_file == "-":
                body = sys.stdin.read()
            else:
                with open(args.body_file, encoding="utf-8") as handle:
                    body = handle.read()
        except (OSError, UnicodeDecodeError) as error:
            print("cannot read --body-file: %s" % error, file=sys.stderr)
            return 1
        # Only trailing whitespace goes: the body itself is the caller's
        # message — passed through, never rewritten. Where the mark lands
        # is attach_mark's call.
        body = body.rstrip()
        if not body:
            print("--body-file is empty: there is no message to mark", file=sys.stderr)
            return 1
        # Local import: check.py imports sigil at load, so a module-level
        # import back would tangle when check.py is run directly.
        import check

        # A quoted or fenced tail gets the mark as its own paragraph, so a
        # mark inside it is someone else's text — only an inline tail can
        # already be marked. A damaged mark is refused too: it wants repair,
        # not a fresh mark burying it.
        if not needs_own_paragraph(body) and check.ends_in_mark(body):
            print("--body-file already ends in a mark: one sigil per contribution", file=sys.stderr)
            return 1

    tooltip = None
    if args.tooltip:
        if args.platform in TOOLTIP_TARGETS:
            tooltip = tooltip_text(args.model, args.text)
        else:
            print(
                "note: --tooltip only applies to --platform %s, ignoring it."
                % " or ".join(TOOLTIP_TARGETS),
                file=sys.stderr,
            )

    url = build_url(
        args.model,
        args.text,
        unapproved=args.unapproved,
        date=args.date,
        agent=args.agent,
    )
    link = format_link(args.platform, url, tooltip)
    print(attach_mark(body, link) if body else link)
    return 0


if __name__ == "__main__":
    sys.exit(main())
