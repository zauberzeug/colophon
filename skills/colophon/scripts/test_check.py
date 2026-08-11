#!/usr/bin/env python3
"""Tests for check.py and the PreToolUse hook — run with: python3 test_check.py"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check  # noqa: E402
import sigil  # noqa: E402

HOOK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "hooks", "colophon_guard.py"
)

LEGEND = "https://zauberzeug.github.io/colophon/#m=claude-opus-5&t=Drafted%20by%20the%20model."


class BareSigil(unittest.TestCase):
    def test_a_text_ending_in_a_naked_sigil_is_rejected(self):
        self.assertEqual(check.find_violations("Ordered the parts. ※"), ["bare-sigil"])

    def test_a_sigil_alone_is_rejected(self):
        self.assertEqual(check.find_violations("※"), ["bare-sigil"])

    def test_trailing_whitespace_does_not_hide_it(self):
        self.assertEqual(check.find_violations("Ordered the parts. ※  \n"), ["bare-sigil"])


class MentionIsNotAMark(unittest.TestCase):
    """A presence check would reject correct behaviour; position is the rule."""

    def test_mid_sentence_mention_passes(self):
        text = "The agent appends the ※ itself — you never type it."
        self.assertEqual(check.find_violations(text), [])

    def test_inline_code_at_the_end_passes(self):
        self.assertEqual(check.find_violations("The character is `※`"), [])

    def test_fenced_example_at_the_end_passes(self):
        self.assertEqual(check.find_violations("Output:\n```\n… ※\n```"), [])

    def test_quoted_line_at_the_end_passes(self):
        self.assertEqual(check.find_violations("Falko wrote:\n> a bare ※ is not intended. ※"), [])


class LinkedMarksPass(unittest.TestCase):
    """Every dialect sigil.py emits must survive its own check."""

    def test_every_platform_output_passes(self):
        for platform in sigil.PLATFORMS + ("html",):
            with self.subTest(platform=platform):
                link = sigil.format_link(platform, LEGEND)
                self.assertEqual(check.find_violations("Ordered the parts. " + link), [])

    def test_markdown_tooltip_variant_passes(self):
        link = sigil.format_link("github", LEGEND, tooltip="claude-opus-5: Drafted by the model.")
        self.assertEqual(check.find_violations("Ordered the parts. " + link), [])

    def test_custom_base_still_passes_through_the_fragment(self):
        link = "<http://localhost:8000/#m=claude-opus-5&t=X|※>"
        self.assertEqual(check.find_violations("Ordered the parts. " + link), [])


class LabelMustBeTheSigil(unittest.TestCase):
    """The observed break: the URL half is encoded, the label half must not be."""

    def test_percent_encoded_label_is_rejected(self):
        text = "Details in the thread. <%s|%%E2%%80%%BB>" % LEGEND
        self.assertEqual(check.find_violations(text), ["link-without-sigil-label"])

    def test_a_word_as_label_is_rejected(self):
        self.assertEqual(
            check.find_violations("Background: <%s|Colophon>" % LEGEND),
            ["link-without-sigil-label"],
        )

    def test_every_dialect_is_covered(self):
        for text in (
            "<%s|%%E2%%80%%BB>" % LEGEND,
            "[%%E2%%80%%BB](%s)" % LEGEND,
            "[%%E2%%80%%BB|%s]" % LEGEND,
            '<a href="%s">%%E2%%80%%BB</a>' % LEGEND,
        ):
            with self.subTest(text=text):
                self.assertEqual(check.find_violations(text), ["link-without-sigil-label"])

    def test_a_link_to_the_repository_keeps_its_own_label(self):
        # The counter-case that decides the rule's shape. Matching on the word
        # "colophon" instead of the #m= fragment would reject every source link
        # to this repo — including the one in its own README.
        text = "Built by Zauberzeug: <https://github.com/zauberzeug/colophon|zauberzeug/colophon>"
        self.assertEqual(check.find_violations(text), [])


class SigilLinksElsewhere(unittest.TestCase):
    def test_trailing_sigil_pointing_somewhere_else_is_rejected(self):
        text = "Report. <https://example.com/notes|※>"
        self.assertEqual(check.find_violations(text), ["sigil-links-elsewhere"])


class Explanations(unittest.TestCase):
    def test_each_rule_names_its_way_out(self):
        self.assertIn("DISPLAY TEXT", check.explain(["link-without-sigil-label"]))
        self.assertIn("sigil.py", check.explain(["bare-sigil"]))
        self.assertIn("sigil.py", check.explain(["sigil-links-elsewhere"]))


class CommandLine(unittest.TestCase):
    def test_clean_text_exits_zero(self):
        self.assertEqual(check.main(["Ordered the parts."]), 0)

    def test_broken_text_exits_nonzero(self):
        self.assertEqual(check.main(["Ordered the parts. ※"]), 1)


class PreToolUseHook(unittest.TestCase):
    """The hook is what actually stands in the way, so it gets driven end to end."""

    def run_hook(self, payload):
        proc = subprocess.run(
            [sys.executable, HOOK],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.strip() else None

    def test_bash_comment_with_a_bare_sigil_is_denied(self):
        out = self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": 'gh issue comment 7 -b "Ordered the parts. ※"'},
            }
        )
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("bare-sigil", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_bash_comment_with_an_encoded_label_is_denied(self):
        out = self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": 'gh issue comment 7 -b "Done. <%s|%%E2%%80%%BB>"' % LEGEND},
            }
        )
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("link-without-sigil-label", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_mcp_tool_arguments_are_walked(self):
        out = self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "mcp__slack__post_message",
                "tool_input": {"channel": "C123", "blocks": [{"text": "Report. ※"}]},
            }
        )
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_a_correct_mark_is_not_denied(self):
        link = sigil.format_link("slack", LEGEND)
        out = self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": 'post "Ordered the parts. %s"' % link},
            }
        )
        self.assertIsNone(out, "a correct mark must pass silently")

    def test_an_ordinary_command_is_not_denied(self):
        out = self.run_hook(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
            }
        )
        self.assertIsNone(out)

    def test_malformed_payload_fails_open(self):
        proc = subprocess.run(
            [sys.executable, HOOK], input="not json", capture_output=True, text=True, timeout=30
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
