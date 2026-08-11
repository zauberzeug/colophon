#!/usr/bin/env python3
"""Tests for sigil.py — run with: python3 test_sigil.py"""

import contextlib
import io
import os
import sys
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sigil  # noqa: E402


def run(argv):
    """Call main() and return (stdout, stderr) with the trailing newline stripped."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        sigil.main(argv)
    return out.getvalue().strip(), err.getvalue()


def fragment_of(url):
    return urlsplit(url).fragment


def params_of(url):
    """Parse the fragment strictly, the way the page does in the browser."""
    return parse_qs(fragment_of(url), keep_blank_values=True)


class TestEncoding(unittest.TestCase):
    def test_umlauts_and_sharp_s(self):
        url = sigil.build_url("claude-opus-5", "Größe, Übermaß, schöner Fluß.")
        self.assertIn("Gr%C3%B6%C3%9Fe", url)
        self.assertIn("%C3%9Cberma%C3%9F", url)
        self.assertEqual(
            params_of(url)["t"][0], "Größe, Übermaß, schöner Fluß."
        )

    def test_special_characters_do_not_break_parameters(self):
        text = 'A & B # C = D 100% "quoted" ?x /y \\z +1'
        url = sigil.build_url("claude-opus-5", text)
        params = params_of(url)
        self.assertEqual(sorted(params), ["m", "t"])
        self.assertEqual(params["t"][0], text)

    def test_everything_is_encoded_including_slash_and_colon(self):
        url = sigil.build_url("claude-opus-5", "see http://example.org/path")
        self.assertNotIn("://example.org", fragment_of(url))
        self.assertIn("%2F", url)
        self.assertIn("%3A", url)

    def test_newlines_become_single_spaces(self):
        url = sigil.build_url("claude-opus-5", sigil.normalize("First line.\n\n  Second\tline."))
        self.assertEqual(params_of(url)["t"][0], "First line. Second line.")

    def test_round_trip(self):
        """The most important test: whatever goes in must come back out unchanged."""
        cases = [
            "Substance from the conversation, wording and structure from the model.",
            "Non-ASCII: äöüÄÖÜß — em dash, „quotes“, 50 % & more.",
            'Punctuation: & # = % " \' < > ? / \\ | + ~ ^ $ * ; , : @ [ ] { }',
            "Emoji and CJK: ✓ ※ 日本語 🙂",
            "  leading and trailing spaces  ",
        ]
        for text in cases:
            with self.subTest(text=text):
                normalized = sigil.normalize(text)
                url = sigil.build_url("claude-opus-5", normalized)
                self.assertEqual(params_of(url)["t"][0], normalized)
                # second route: split the fragment by hand, the way a naive parser would
                pairs = dict(
                    part.split("=", 1) for part in fragment_of(url).split("&")
                )
                self.assertEqual(unquote(pairs["t"]), normalized)


class TestPlatforms(unittest.TestCase):
    ARGS = ["--model", "claude-opus-5", "--text", "Drafted by the model."]

    def test_slack(self):
        out, _ = run(["--platform", "slack"] + self.ARGS)
        self.assertTrue(out.startswith("<https://"))
        self.assertTrue(out.endswith("|※>"))

    def test_jira(self):
        out, _ = run(["--platform", "jira"] + self.ARGS)
        self.assertTrue(out.startswith("[※|https://"))
        self.assertTrue(out.endswith("]"))

    def test_github(self):
        out, _ = run(["--platform", "github"] + self.ARGS)
        self.assertTrue(out.startswith("[※](https://"))
        self.assertTrue(out.endswith(")"))
        self.assertNotIn('"', out)

    def test_trello(self):
        out, _ = run(["--platform", "trello"] + self.ARGS)
        self.assertTrue(out.startswith("[※](https://"))
        self.assertTrue(out.endswith(")"))

    def test_output_is_exactly_one_line(self):
        for platform in sigil.PLATFORMS:
            with self.subTest(platform=platform):
                out, _ = run(["--platform", platform] + self.ARGS)
                self.assertEqual(len(out.splitlines()), 1)

    def test_sigil_is_a_single_codepoint(self):
        self.assertEqual(len(sigil.SIGIL), 1)
        self.assertEqual(ord(sigil.SIGIL), 0x203B)


class TestTooltip(unittest.TestCase):
    def test_github_tooltip_carries_model_and_text(self):
        out, err = run(
            [
                "--platform", "github",
                "--model", "claude-opus-5",
                "--text", "Wording from the model, substance from the author.",
                "--tooltip",
            ]
        )
        self.assertIn(
            '"claude-opus-5: Wording from the model, substance from the author."', out
        )
        self.assertEqual(err, "")

    def test_tooltip_on_other_platform_warns_but_link_is_correct(self):
        for platform in ("slack", "jira", "trello"):
            with self.subTest(platform=platform):
                out, err = run(
                    [
                        "--platform", platform,
                        "--model", "claude-opus-5",
                        "--text", "Drafted by the model.",
                        "--tooltip",
                    ]
                )
                self.assertIn("--tooltip", err)
                plain, _ = run(
                    [
                        "--platform", platform,
                        "--model", "claude-opus-5",
                        "--text", "Drafted by the model.",
                    ]
                )
                self.assertEqual(out, plain)

    def test_quotes_in_tooltip_are_escaped(self):
        out, _ = run(
            [
                "--platform", "github",
                "--model", "claude-opus-5",
                "--text", 'They said "hello" \\ and left.',
                "--tooltip",
            ]
        )
        self.assertIn('\\"hello\\"', out)
        self.assertIn("\\\\", out)
        self.assertTrue(out.endswith('."')  or out.endswith('")'))


class TestSelfPosted(unittest.TestCase):
    def test_without_flag_there_is_no_p_parameter(self):
        url = sigil.build_url("claude-opus-5", "Drafted by the model.")
        self.assertNotIn("p=", url)
        self.assertNotIn("p", params_of(url))

    def test_with_flag_p_is_agent(self):
        url = sigil.build_url("claude-opus-5", "Drafted by the model.", self_posted=True)
        self.assertEqual(params_of(url)["p"], ["agent"])

    def test_cli_flag(self):
        out, _ = run(
            [
                "--platform", "slack",
                "--model", "claude-opus-5",
                "--text", "Assembled by the agent from the ticket history.",
                "--self-posted",
            ]
        )
        self.assertIn("&p=agent", out)


class TestOptionalParameters(unittest.TestCase):
    def test_date_and_agent(self):
        url = sigil.build_url(
            "claude-opus-5", "Drafted by the model.", date="2026-08-10", agent="claude-code"
        )
        params = params_of(url)
        self.assertEqual(params["d"], ["2026-08-10"])
        self.assertEqual(params["a"], ["claude-code"])

    def test_omitted_optionals_do_not_appear(self):
        params = params_of(sigil.build_url("claude-opus-5", "Drafted by the model."))
        self.assertEqual(sorted(params), ["m", "t"])

    def test_parameter_order_is_stable(self):
        url = sigil.build_url(
            "claude-opus-5",
            "Drafted by the model.",
            self_posted=True,
            date="2026-08-10",
            agent="claude-code",
        )
        keys = [part.split("=", 1)[0] for part in fragment_of(url).split("&")]
        self.assertEqual(keys, ["m", "t", "p", "d", "a"])


class TestErrors(unittest.TestCase):
    def assert_exits_nonzero(self, argv):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                sigil.main(argv)
        self.assertNotEqual(caught.exception.code, 0)

    def test_empty_text(self):
        self.assert_exits_nonzero(
            ["--platform", "slack", "--model", "claude-opus-5", "--text", "   "]
        )

    def test_missing_text(self):
        self.assert_exits_nonzero(["--platform", "slack", "--model", "claude-opus-5"])

    def test_empty_model(self):
        self.assert_exits_nonzero(
            ["--platform", "slack", "--model", " ", "--text", "Drafted by the model."]
        )

    def test_unknown_platform(self):
        self.assert_exits_nonzero(
            ["--platform", "discord", "--model", "claude-opus-5", "--text", "Drafted."]
        )

    def test_malformed_date(self):
        self.assert_exits_nonzero(
            [
                "--platform", "slack",
                "--model", "claude-opus-5",
                "--text", "Drafted by the model.",
                "--date", "10.08.2026",
            ]
        )


class TestBaseUrl(unittest.TestCase):
    def test_default_base(self):
        url = sigil.build_url("claude-opus-5", "Drafted by the model.")
        self.assertTrue(url.startswith("https://zauberzeug.github.io/colophon/#"))

    def test_env_override(self):
        old = os.environ.get("COLOPHON_BASE")
        os.environ["COLOPHON_BASE"] = "http://localhost:8000/"
        try:
            url = sigil.build_url("claude-opus-5", "Drafted by the model.")
            self.assertTrue(url.startswith("http://localhost:8000/#"))
        finally:
            if old is None:
                del os.environ["COLOPHON_BASE"]
            else:
                os.environ["COLOPHON_BASE"] = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
