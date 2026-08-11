#!/usr/bin/env python3
"""Reject a colophon that arrives broken.

The sigil is not a decoration, it is a link: the statement lives on the page
behind it. Two ways that link comes apart, both observed in the first day of
real use, both invisible to the agent that caused them:

    bare-sigil                  a text ends with a naked ``※`` and no link
    link-without-sigil-label    a link to the legend page whose label is not ``※``
    sigil-links-elsewhere       a trailing ``※`` links somewhere other than the legend

The second one is worth spelling out, because it looks like a typo and is not.
``sigil.py`` emits ``<URL|※>``; the URL half is percent-encoded throughout
(``%20``, ``%3B``, ``%2C``) and the label half must stay literal. An agent
copying that line into a posting script wrote ``%E2%80%BB`` — the percent-encoded
form of the character — into the label. The link worked; the reader saw eight
literal characters where the mark should be.

Nothing in the sigil's own output can prevent that: the corruption happens
after the script has printed the right answer. It needs a check at the write
path, which is what this module is for. ``hooks/colophon_guard.py`` wires it
into Claude Code as a ``PreToolUse`` hook; other integrations call
``find_violations`` from wherever their own outgoing text is assembled.

Position matters, not presence. Only a sigil in trailing position is a *mark*
and must be a link; mid-sentence it is a *mention*, and anyone documenting or
discussing the system writes plenty of those. A presence check rejects correct
behaviour, which is how a guard earns its way out of a codebase.
"""

import argparse
import re
import sys

SIGIL = "※"  # ※ REFERENCE MARK

# Code spans hold examples, not marks.
_CODE_SPAN = re.compile(r"```.*?```|`[^`]*`", re.DOTALL)

# The link dialects sigil.py emits, anchored at the end of the text — the only
# place a mark may stand.
_TRAILING_LINK = (
    re.compile(r"<(?P<url>[^<>|]+)\|" + SIGIL + r"\s*>\s*$"),                            # slack
    re.compile(r"\[" + SIGIL + r"\]\(\s*(?P<url>[^\s()]+)(?:\s+\"[^\"]*\")?\s*\)\s*$"),  # markdown
    re.compile(r"\[" + SIGIL + r"\|(?P<url>[^\]]+)\]\s*$"),                              # jira
    re.compile(                                                                          # html
        r"<a\s[^>]*href=[\"'](?P<url>[^\"']+)[\"'][^>]*>\s*" + SIGIL + r"\s*</a>\s*$",
        re.IGNORECASE,
    ),
)

# The same dialects, unanchored and capturing the label: a legend link is a
# mark wherever it stands.
_ANY_LINK = (
    re.compile(r"<(?P<url>[^<>|]+)\|(?P<label>[^<>]*)>"),
    re.compile(r"\[(?P<label>[^\]]*)\]\(\s*(?P<url>[^\s()]+)(?:\s+\"[^\"]*\")?\s*\)"),
    re.compile(r"\[(?P<label>[^\]|]*)\|(?P<url>[^\]]+)\]"),
    re.compile(r"<a\s[^>]*href=[\"'](?P<url>[^\"']+)[\"'][^>]*>(?P<label>[^<]*)</a>", re.IGNORECASE),
)


def is_legend_url(url):
    """A link to the colophon page, recognised by the fragment, not the host.

    ``sigil.py`` always builds ``#m=<model>``, whatever ``COLOPHON_BASE`` says.
    Matching on the word "colophon" instead would swallow links to the
    repository, which are ordinary source links and keep their own label.
    """
    candidate = (url or "").strip()
    return bool(re.match(r"^https?://", candidate, re.IGNORECASE)) and "#m=" in candidate


def _ends_in_quotation(text):
    lines = [line for line in text.splitlines() if line.strip()]
    return bool(lines) and lines[-1].lstrip().startswith(">")


def find_violations(text):
    """Return stable rule names for a colophon that is not a working link."""
    body = (text or "").rstrip()
    violations = []

    for pattern in _ANY_LINK:
        for match in pattern.finditer(body):
            if is_legend_url(match.group("url")) and match.group("label").strip() != SIGIL:
                violations.append("link-without-sigil-label")
                break
        if violations:
            break

    if SIGIL not in body:
        return violations

    for pattern in _TRAILING_LINK:
        match = pattern.search(body)
        if match:
            if not is_legend_url(match.group("url")):
                violations.append("sigil-links-elsewhere")
            return violations

    if _ends_in_quotation(body):
        return violations

    masked = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), body).rstrip()
    if masked.endswith(SIGIL):
        violations.append("bare-sigil")
    return violations


def explain(violations):
    """One actionable sentence per rule, addressed to whoever wrote the text."""
    if "link-without-sigil-label" in violations:
        return (
            "A link to the colophon page does not carry the sigil as its label. In <url|label> "
            "and [label](url) everything after the separator is DISPLAY TEXT: the literal "
            "character belongs there, not its percent-encoded form (%E2%80%BB) and not a word. "
            "Only the URL is encoded. Paste the output of sigil.py unchanged instead of "
            "retyping it."
        )
    if "sigil-links-elsewhere" in violations:
        return (
            "The trailing sigil links somewhere other than the colophon page. The mark IS the "
            "link — build it with sigil.py and use the output verbatim."
        )
    return (
        "The text ends in a bare sigil. Without its link the mark says nothing at all: the "
        "model, the date and the division of labour live on the page behind it. Either drop "
        "the mark (ordinary chat, reminders and questions do not carry one) or build it with "
        "sigil.py and put the output at the end."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check that a colophon sigil in a text is a working link.",
    )
    parser.add_argument("text", nargs="?", default="-", help="text to check, or '-' for stdin")
    args = parser.parse_args(argv)
    text = sys.stdin.read() if args.text == "-" else args.text
    violations = find_violations(text)
    if not violations:
        return 0
    print("%s [%s]" % (explain(violations), ", ".join(violations)), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
