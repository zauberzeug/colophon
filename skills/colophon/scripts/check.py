#!/usr/bin/env python3
"""Reject a colophon that arrives broken.

The sigil is not a decoration, it is a link: the statement lives on the page
behind it. Two ways the link comes apart, both observed in the first day of
real use, both invisible to the agent that caused them: a text ends in a naked
``※`` with no link at all, or the link is built and its label is ``%E2%80%BB``
— the percent-encoded form of the character, right in the URL half and wrong
in the display half. Nothing in ``sigil.py``'s own output can prevent either;
the damage happens after it has printed the right answer. So the rule lives
here, for whatever assembles outgoing text — an agent gateway, a bot
framework, a posting script — to call at its write path.

Position, not presence: only a sigil in trailing position is a mark and must
be a working link. Mid-sentence it is a mention, a code span holds an example,
and a lone ``※`` is a label field in a structured payload that keeps href and
label apart — all of that passes untouched, because the rule never looks at
anything but the tail. The deliberate price: a bare sigil that is *not* the
last thing in the text escapes.
"""

import re
import sys

SIGIL = "※"  # U+203B REFERENCE MARK
ENCODED = "%E2%80%BB"  # its percent-encoding — right in the URL, wrong as a label

# A correct mark: the four link dialects sigil.py emits, at the very end.
_GOOD_TAIL = re.compile(
    r"(?:<[^<>|]+\|" + SIGIL + r"\s*>"                      # slack
    r"|\[" + SIGIL + r"\]\([^\s()]+(?:\s+\"[^\"]*\")?\)"    # markdown
    r"|\[" + SIGIL + r"\|[^\]]+\]"                          # jira
    r"|<a\s[^>]*>\s*" + SIGIL + r"\s*</a>)\s*$"             # html
)
# The same shapes with the label captured, whatever it turned out to be.
_TAIL_LINK = re.compile(
    r"(?:<[^<>|]*\|([^<>]*)>"
    r"|\[([^\]]*)\]\([^\s()]*(?:\s+\"[^\"]*\")?\)"
    r"|\[([^\]|]*)\|[^\]]*\]"
    r"|<a\s[^>]*>([^<]*)</a>)\s*$",
    re.IGNORECASE,
)

REASON = (
    "The text ends in a broken colophon: a naked ※ without its link, or a link whose label "
    "is the percent-encoded %E2%80%BB. The mark IS the link, and only the URL half is "
    "encoded — everything after the separator is DISPLAY TEXT and carries the literal "
    "character. Build the mark with sigil.py and paste its output unchanged at the end; "
    "if no marking was intended, drop the character."
)


def is_broken_mark(text):
    """True if the text ends in something sigil-shaped that is not a working mark."""
    tail = (text or "").rstrip()
    if tail == SIGIL:
        return False  # a label field in a structured payload, not a message
    if _GOOD_TAIL.search(tail):
        return False
    match = _TAIL_LINK.search(tail)
    if match:
        label = next(group for group in match.groups() if group is not None)
        return ENCODED in label.upper()
    return tail.endswith(SIGIL)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = sys.stdin.read() if argv in ([], ["-"]) else argv[0]
    if not is_broken_mark(text):
        return 0
    print(REASON, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
