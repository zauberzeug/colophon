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
framework, a posting script — to call at its write path. It imports
``sigil.py``, so the two files travel together.

The tail patterns are derived, not transcribed: a sentinel URL is formatted
through ``sigil.format_link`` for every mark target (and tooltip variant),
escaped, and the sentinel parts replaced by subpatterns. One shape source — a
target added to ``sigil.MARK_TARGETS`` is guarded automatically, and the
patterns cannot drift from what ``sigil.py`` actually emits. ``json`` and
``url`` stay out by tuple: they hand over pieces for a caller to assemble, so
damage to them is caught at assembly (``label_field=True``), not in a tail.

Position, not presence: only a sigil in trailing position is a mark. A
trailing link in one of ``sigil.py``'s shapes must carry the literal ``※`` as
its label; a label that is the percent-encoding is the observed damage, and a
link to the legend page (``#m=`` in the URL) labelled anything else has lost
its mark the same way. A trailing naked ``※`` or ``%E2%80%BB`` is broken.
Everything else passes untouched: mid-sentence mentions, code spans, links
whose label merely talks about the encoding, and lines quoted with ``>``.
Callers that check a structured payload's label field pass
``label_field=True`` so a field holding exactly the character stays legal.

The deliberate prices of the tail rule, in the open: damage that is not the
last thing in the text escapes (``… ※ [docs](…)``, ``… ※.``, a footer after
the mark, a damaged link mid-text), a mark buried deeper than ``TAIL_BOUND``
escapes the bounded scan, a text whose last line is a quotation is never
checked at all — and a sentence that legitimately *ends* in the bare
character is flagged, which writing it as a code span avoids.
"""

import re
import sys
from urllib.parse import quote

import sigil
from sigil import SIGIL

ENCODED = quote(SIGIL)  # "%E2%80%BB" — right in the URL, wrong as a label

# The patterns only ever need the end of the text; bounding what they see
# keeps the scan cheap on adversarial input (a real mark measures ~2 KB).
TAIL_BOUND = 4096

# The sentinels survive every dialect's escaping unchanged, so after
# re.escape they can be swapped for subpatterns.
_URL = "https://sentinel.invalid/x"
_TOOLTIP = "sentineltooltip"
_URL_SUB = r'(?P<url>[^\s<>|\[\]()"]+)'
_TITLE_SUB = r'(?:[^"\\]|\\.)*'


def _label_sub(template):
    """A capture that cannot cross the delimiters bounding the label in this template."""
    index = template.index(SIGIL)
    bounds = template[index - 1 : index] + template[index + len(SIGIL) : index + len(SIGIL) + 1]
    return r"(?P<label>[^%s]*)" % re.escape(bounds)


def _tail_patterns():
    """One anchored pattern per finished-mark shape sigil.py emits — derived, not transcribed."""
    variants = [(target, None) for target in sigil.MARK_TARGETS]
    variants += [(target, _TOOLTIP) for target in sigil.TOOLTIP_TARGETS]
    patterns = {}
    for target, tooltip in variants:
        template = sigil.format_link(target, _URL, tooltip=tooltip)
        pattern = re.escape(template)
        pattern = pattern.replace(re.escape(_URL), _URL_SUB)
        if tooltip:
            pattern = pattern.replace(re.escape(tooltip), _TITLE_SUB)
        pattern = pattern.replace(re.escape(SIGIL), _label_sub(template))
        patterns[pattern] = re.compile(pattern + r"$")
    return list(patterns.values())


_TAIL_PATTERNS = _tail_patterns()

REASON = (
    "The text ends in a broken colophon: a naked %(sigil)s (or its percent-encoding "
    "%(encoded)s) without its link, or a trailing link that should carry the mark but "
    "whose label is not the literal character. Only the URL half of a link is "
    "percent-encoded; the label half is display text and carries %(sigil)s itself — "
    "after the | in Slack's <url|%(sigil)s>, before the | in Jira's [%(sigil)s|url], "
    "inside the brackets in markdown's [%(sigil)s](url). Build the mark with sigil.py "
    "and paste its output unchanged at the end; if no marking was intended, drop the "
    "character."
) % {"sigil": SIGIL, "encoded": ENCODED}

USAGE = "usage: check.py [TEXT | -]   (one argument; `-` or no argument reads stdin)"


def _is_legend_url(url):
    """The schema build_url writes: a fragment opening with m= and carrying t=."""
    fragment = url.rpartition("#")[2]
    return fragment.startswith("m=") and ("&t=" in fragment or "&amp;t=" in fragment)


def is_broken_mark(text, label_field=False):
    """True if the text ends in something sigil-shaped that is not a working mark."""
    tail = (text or "").rstrip()
    if label_field and tail.strip() == SIGIL:
        return False  # a label beside its own href field, not a message
    if tail.rsplit("\n", 1)[-1].lstrip().startswith(">"):
        return False  # the tail is a quotation — someone else's text
    tail = tail[-TAIL_BOUND:]
    for pattern in _TAIL_PATTERNS:
        match = pattern.search(tail)
        if not match:
            continue
        label = match.group("label").strip()
        if label == SIGIL:
            return False
        if label.upper() == ENCODED:
            return True  # the observed damage: the encoding where the character belongs
        return _is_legend_url(match.group("url"))  # a legend link labelled anything else lost its mark
    return tail.endswith(SIGIL) or tail.upper().endswith(ENCODED)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if len(argv) > 1:
        print(USAGE, file=sys.stderr)
        print("error: got %d arguments — quote the text so it arrives as one" % len(argv), file=sys.stderr)
        return 2
    text = sys.stdin.read() if argv in ([], ["-"]) else argv[0]
    if not is_broken_mark(text):
        return 0
    print(REASON, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
