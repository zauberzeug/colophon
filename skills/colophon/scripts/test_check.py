#!/usr/bin/env python3
"""Tests for check.py — run with: python3 test_check.py"""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check  # noqa: E402
import sigil  # noqa: E402

MODEL = "claude-opus-5"
TEXT = "Drafted by the model."
QUOTED_TEXT = 'He said "go".'
# Fixtures come from sigil's own helpers (base pinned so COLOPHON_BASE cannot
# skew them), so they track what sigil.py actually emits.
LEGEND = sigil.build_url(MODEL, TEXT, base=sigil.DEFAULT_BASE)
QUOTED_LEGEND = sigil.build_url(MODEL, QUOTED_TEXT, base=sigil.DEFAULT_BASE)
TOOLTIP = sigil.tooltip_text(MODEL, TEXT)
QUOTED_TOOLTIP = sigil.tooltip_text(MODEL, QUOTED_TEXT)


def run_cli(argv, stdin=None):
    """Call check.main with captured stdout/stderr; returns (exit, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if stdin is not None:
            original = sys.stdin
            sys.stdin = io.StringIO(stdin)
            try:
                code = check.main(argv)
            finally:
                sys.stdin = original
        else:
            code = check.main(argv)
    return code, out.getvalue(), err.getvalue()


class EveryDialectPasses(unittest.TestCase):
    """Every output sigil.py emits must survive its own check.

    Coverage derives from the TARGETS/TOOLTIP_TARGETS tuples and the patterns
    themselves derive from format_link, so a new target added there is
    exercised — and guarded — automatically.
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

    def test_a_tooltip_containing_a_quote_still_passes(self):
        for target in sigil.TOOLTIP_TARGETS:
            with self.subTest(target=target):
                link = sigil.format_link(target, QUOTED_LEGEND, tooltip=QUOTED_TOOLTIP)
                self.assertFalse(check.is_broken_mark("Ordered the parts. " + link))


class TheTwoIncidents(unittest.TestCase):
    """The observed failures, the reason this module exists."""

    def test_a_text_ending_in_a_naked_sigil_is_broken(self):
        self.assertTrue(check.is_broken_mark("Ordered the parts. ※"))

    def test_a_message_that_is_only_the_sigil_is_broken(self):
        self.assertTrue(check.is_broken_mark("※"))

    def test_trailing_whitespace_does_not_hide_it(self):
        self.assertTrue(check.is_broken_mark("Ordered the parts. ※  \n"))

    def test_a_naked_encoded_sigil_is_broken_too(self):
        # The same mistake — the encoding where the character belongs —
        # without any link wrapping around it.
        self.assertTrue(check.is_broken_mark("Ordered the parts. %E2%80%BB"))

    def test_an_encoded_label_is_broken_in_every_dialect(self):
        # sigil.py's output carries the sigil exactly once, as the label; the
        # incident wrote its percent-encoding there instead.
        for target in sigil.TARGETS:
            link = sigil.format_link(target, LEGEND)
            if check.SIGIL not in link:  # `url` emits no label to damage
                continue
            with self.subTest(target=target):
                damaged = link.replace(check.SIGIL, "%E2%80%BB")
                self.assertTrue(check.is_broken_mark("Done. " + damaged))

    def test_an_encoded_label_is_broken_with_a_quoted_tooltip(self):
        # The title carries escaped quotes (markdown) or entities (html);
        # neither may hide the damaged label from the derived patterns.
        for target in sigil.TOOLTIP_TARGETS:
            with self.subTest(target=target):
                link = sigil.format_link(target, QUOTED_LEGEND, tooltip=QUOTED_TOOLTIP)
                damaged = link.replace(check.SIGIL, "%E2%80%BB")
                self.assertTrue(check.is_broken_mark("Done. " + damaged))

    def test_lowercase_encoding_is_still_caught(self):
        self.assertTrue(check.is_broken_mark("Done. <%s|%%e2%%80%%bb>" % LEGEND))


class LostLabels(unittest.TestCase):
    """A legend link labelled anything but the sigil renders as that text."""

    def test_a_word_label_on_a_legend_link_is_broken(self):
        self.assertTrue(check.is_broken_mark("Done. [see colophon](%s)" % LEGEND))

    def test_an_empty_label_on_a_legend_link_is_broken(self):
        self.assertTrue(check.is_broken_mark("Done. <%s|>" % LEGEND))

    def test_an_encoded_label_is_broken_even_on_a_foreign_url(self):
        self.assertTrue(check.is_broken_mark("Done. <https://example.com/x|%E2%80%BB>"))

    def test_a_word_label_on_a_foreign_link_passes(self):
        self.assertFalse(check.is_broken_mark("Done. [docs](https://example.com/docs)"))

    def test_a_foreign_fragment_starting_with_m_is_not_a_legend_url(self):
        self.assertFalse(check.is_broken_mark("Done. [docs](https://example.com/page#m=2)"))


class MentionsAreNotMarks(unittest.TestCase):
    """Position, not presence: a presence check would reject correct writing."""

    def test_mid_sentence_mention_passes(self):
        self.assertFalse(check.is_broken_mark("The agent appends the ※ itself — you never type it."))

    def test_code_span_at_the_end_passes(self):
        self.assertFalse(check.is_broken_mark("The character is `※`"))

    def test_encoding_mention_in_a_code_span_passes(self):
        self.assertFalse(check.is_broken_mark("The encoded form is `%E2%80%BB`"))

    def test_a_label_merely_mentioning_the_encoding_passes(self):
        text = "Root cause: [the %E2%80%BB bug](https://github.com/zauberzeug/colophon/pull/3)"
        self.assertFalse(check.is_broken_mark(text))

    def test_a_quoted_broken_line_passes(self):
        self.assertFalse(check.is_broken_mark("The bot posted:\n> Ordered the parts. ※"))

    def test_a_prose_link_beside_a_correct_mark_passes(self):
        text = "See the [colophon page](%s) for details. [※](%s)" % (LEGEND, LEGEND)
        self.assertFalse(check.is_broken_mark(text))

    def test_a_repository_link_keeps_its_own_label(self):
        text = "Built by Zauberzeug: [zauberzeug/colophon](https://github.com/zauberzeug/colophon)"
        self.assertFalse(check.is_broken_mark(text))


class LabelFields(unittest.TestCase):
    """Payloads that keep href and label apart opt in via label_field=True."""

    def test_a_lone_sigil_label_field_passes(self):
        # `--platform url` callers hold exactly the character in the label
        # field; the caller knows it is a field, so the caller says so.
        for value in ("※", " ※", "※\n"):
            with self.subTest(value=value):
                self.assertFalse(check.is_broken_mark(value, label_field=True))

    def test_a_damaged_label_field_is_still_broken(self):
        self.assertTrue(check.is_broken_mark("%E2%80%BB", label_field=True))


class DeliberateGaps(unittest.TestCase):
    """The price of the tail rule, pinned so a change to it is a decision."""

    def test_a_sigil_that_is_not_final_escapes(self):
        self.assertFalse(check.is_broken_mark("Ordered. ※ [docs](https://example.com)"))

    def test_a_sigil_before_closing_punctuation_escapes(self):
        self.assertFalse(check.is_broken_mark("Ordered the parts. ※."))

    def test_a_sigil_before_a_footer_escapes(self):
        self.assertFalse(check.is_broken_mark("Ordered the parts. ※\n\n-- The Bot"))

    def test_mid_text_damage_escapes(self):
        self.assertFalse(check.is_broken_mark("Done. <%s|%%E2%%80%%BB> Thanks!" % LEGEND))

    def test_a_quoted_last_line_is_never_checked(self):
        # The quotation exemption cannot tell quoted damage from new damage
        # a blockquote-formatted sender produces itself.
        self.assertFalse(check.is_broken_mark("> I ordered the parts myself. ※"))


class BoundedTail(unittest.TestCase):
    def test_a_damaged_mark_behind_a_huge_prefix_is_still_caught(self):
        text = "y" * 100000 + "\nDone. <%s|%%E2%%80%%BB>" % LEGEND
        self.assertTrue(check.is_broken_mark(text))

    def test_a_bracket_flood_passes_without_stalling(self):
        # The derived character classes scan linearly; TAIL_BOUND caps even
        # a pathological future shape.
        self.assertFalse(check.is_broken_mark("[" * 100000))


class CommandLine(unittest.TestCase):
    def test_clean_text_exits_zero_and_stays_silent(self):
        code, out, err = run_cli(["Ordered the parts."])
        self.assertEqual((code, out, err), (0, "", ""))

    def test_broken_text_exits_one_with_the_reason_on_stderr(self):
        code, out, err = run_cli(["Ordered the parts. ※"])
        self.assertEqual((code, out), (1, ""))
        self.assertIn("broken colophon", err)

    def test_stdin_is_checked_when_no_argument_is_given(self):
        code, _, err = run_cli([], stdin="Ordered the parts. ※")
        self.assertEqual(code, 1)
        self.assertIn("broken colophon", err)

    def test_extra_arguments_error_instead_of_checking_one_word(self):
        # An unquoted invocation must fail loudly, not pass on argv[0].
        code, _, err = run_cli(["Ordered", "the", "parts.", "※"])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)

    def test_help_prints_usage(self):
        code, out, _ = run_cli(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("usage:", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
