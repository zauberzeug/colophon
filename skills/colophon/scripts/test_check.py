#!/usr/bin/env python3
"""Tests for check.py — run with: python3 test_check.py"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check  # noqa: E402
import sigil  # noqa: E402

LEGEND = "https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Drafted%20by%20the%20model."
TOOLTIP = "claude-opus-5: Drafted by the model."


class EveryDialectPasses(unittest.TestCase):
    """Every output sigil.py emits must survive its own check.

    Coverage derives from the TARGETS/TOOLTIP_TARGETS tuples, so a new target
    added there is exercised automatically.
    """

    def test_every_target_output_passes(self):
        for target in sigil.TARGETS:
            with self.subTest(target=target):
                link = sigil.format_link(target, LEGEND)
                self.assertFalse(check.is_broken_mark("Ordered the parts. " + link))

    def test_every_tooltip_variant_passes(self):
        for target in sigil.TOOLTIP_TARGETS:
            with self.subTest(target=target):
                link = sigil.format_link(target, LEGEND, tooltip=TOOLTIP)
                self.assertFalse(check.is_broken_mark("Ordered the parts. " + link))

    def test_check_and_sigil_agree_on_the_character(self):
        self.assertEqual(check.SIGIL, sigil.SIGIL)


class TheTwoIncidents(unittest.TestCase):
    """The observed failures, the reason this module exists."""

    def test_a_text_ending_in_a_naked_sigil_is_broken(self):
        self.assertTrue(check.is_broken_mark("Ordered the parts. ※"))

    def test_trailing_whitespace_does_not_hide_it(self):
        self.assertTrue(check.is_broken_mark("Ordered the parts. ※  \n"))

    def test_an_encoded_label_is_broken_in_every_dialect(self):
        # A mark dialect's output carries the sigil exactly once, as the
        # label; the incident wrote its percent-encoding there instead.
        # `json` and `url` are not in MARK_TARGETS: they hand over pieces, and
        # damage to a piece is caught where the pieces are assembled, not here.
        for target in sigil.MARK_TARGETS:
            with self.subTest(target=target):
                link = sigil.format_link(target, LEGEND)
                damaged = link.replace(check.SIGIL, "%E2%80%BB")
                self.assertTrue(check.is_broken_mark("Done. " + damaged))

    def test_lowercase_encoding_is_still_caught(self):
        self.assertTrue(check.is_broken_mark("Done. <%s|%%e2%%80%%bb>" % LEGEND))


class MentionsAreNotMarks(unittest.TestCase):
    """Position, not presence: a presence check would reject correct writing."""

    def test_mid_sentence_mention_passes(self):
        self.assertFalse(check.is_broken_mark("The agent appends the ※ itself — you never type it."))

    def test_code_span_at_the_end_passes(self):
        self.assertFalse(check.is_broken_mark("The character is `※`"))

    def test_a_lone_sigil_is_a_label_field_not_a_message(self):
        # `--platform url` callers keep href and label apart; the label field
        # holds exactly the character and must not read as a bare mark.
        self.assertFalse(check.is_broken_mark("※"))

    def test_a_prose_link_beside_a_correct_mark_passes(self):
        text = "See the [colophon page](%s) for details. [※](%s)" % (LEGEND, LEGEND)
        self.assertFalse(check.is_broken_mark(text))

    def test_a_repository_link_keeps_its_own_label(self):
        text = "Built by Zauberzeug: [zauberzeug/colophon](https://github.com/zauberzeug/colophon)"
        self.assertFalse(check.is_broken_mark(text))

    def test_the_deliberate_price_a_sigil_that_is_not_final_escapes(self):
        # The mark is defined as trailing; this failure nobody has produced.
        self.assertFalse(check.is_broken_mark("Ordered. ※ [docs](https://example.com)"))


class CommandLine(unittest.TestCase):
    def test_clean_text_exits_zero(self):
        self.assertEqual(check.main(["Ordered the parts."]), 0)

    def test_broken_text_exits_one(self):
        self.assertEqual(check.main(["Ordered the parts. ※"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
