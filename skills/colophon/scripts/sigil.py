#!/usr/bin/env python3
"""Build the Colophon sigil as a ready-to-paste link for Slack, Jira, GitHub and Trello.

Prints exactly one line to stdout. Warnings go to stderr so the output stays
usable in a pipe.

    sigil.py --platform slack --model claude-opus-5 --text "Drafted by the model."
"""

import argparse
import datetime
import os
import re
import sys
from urllib.parse import quote

DEFAULT_BASE = "https://zauberzeug.github.io/colophon/"

SIGIL = "※"  # U+203B REFERENCE MARK

PLATFORMS = ("slack", "jira", "github", "trello")


def base_url():
    """Return the base URL, overridable via the COLOPHON_BASE environment variable."""
    return (os.environ.get("COLOPHON_BASE") or DEFAULT_BASE).strip().rstrip("#")


def normalize(text):
    """Collapse newlines and runs of whitespace into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def build_url(model, text, self_posted=False, date=None, agent=None, base=None):
    """Assemble the Colophon URL: everything in the fragment, everything encoded."""
    params = [("m", model), ("t", text)]
    if self_posted:
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
    if platform == "slack":
        return "<%s|%s>" % (url, SIGIL)
    if platform == "jira":
        return "[%s|%s]" % (SIGIL, url)
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
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
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
        help="append a hover title; only effective with --platform github",
    )
    parser.add_argument(
        "--self-posted",
        action="store_true",
        help="set p=agent — only when the agent publishes the contribution itself",
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
        if args.platform == "github":
            tooltip = tooltip_text(args.model, args.text)
        else:
            print(
                "note: --tooltip only applies to --platform github, ignoring it.",
                file=sys.stderr,
            )

    url = build_url(
        args.model,
        args.text,
        self_posted=args.self_posted,
        date=args.date,
        agent=args.agent,
    )
    print(format_link(args.platform, url, tooltip))
    return 0


if __name__ == "__main__":
    sys.exit(main())
