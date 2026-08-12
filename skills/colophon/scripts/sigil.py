#!/usr/bin/env python3
"""Build the Colophon sigil as a ready-to-paste link for Slack, Jira, GitHub and Trello.

Prints exactly one line to stdout. Warnings go to stderr so the output stays
usable in a pipe.

    sigil.py --platform slack --model claude-opus-5 --text "Drafted by the model."

Two targets are not platforms: `--platform html` emits an anchor for anything
whose body is markup (an HTML mail, a Confluence page), and `--platform url`
prints the bare URL for callers that build the link themselves (Jira ADF, an
API payload that keeps href and label apart).
"""

import argparse
import datetime
import html
import os
import re
import sys
from urllib.parse import quote

DEFAULT_BASE = "https://zauberzeug.github.io/colophon/"

SIGIL = "※"  # U+203B REFERENCE MARK

PLATFORMS = ("slack", "jira", "github", "trello")

# Neither of these is a platform, so both stay out of PLATFORMS and that
# remains the list of destinations whose dialect you cannot guess from the
# name. `html` is a dialect named after its syntax — an HTML mail body is the
# common case, but so is a Confluence page. `url` emits no link at all, for
# callers that build one themselves and only need the href.
TARGETS = PLATFORMS + ("html", "url")

# Dialects whose syntax carries a native hover title.
TOOLTIP_TARGETS = ("github", "html")


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
        "`url` the bare URL for callers that build the link themselves",
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
    print(format_link(args.platform, url, tooltip))
    return 0


if __name__ == "__main__":
    sys.exit(main())
