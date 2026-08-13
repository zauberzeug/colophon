#!/usr/bin/env python3
"""Tests for sigil.py — run with: python3 test_sigil.py"""

import contextlib
import html
import io
import json
import os
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, unquote, urlsplit
from xml.etree import ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check  # noqa: E402
import sigil  # noqa: E402


def run(argv, stdin=None):
    """Call main() and return (stdout, stderr) with the trailing newline stripped."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if stdin is None:
            sigil.main(argv)
        else:
            original = sys.stdin
            sys.stdin = io.StringIO(stdin)
            try:
                sigil.main(argv)
            finally:
                sys.stdin = original
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

    def test_html_is_an_anchor(self):
        out, _ = run(["--platform", "html"] + self.ARGS)
        self.assertTrue(out.startswith('<a href="https://'))
        self.assertTrue(out.endswith(">※</a>"))

    def test_html_escapes_ampersands_in_the_href(self):
        """Bare, the & is a parse error in XML and a character reference in HTML."""
        out, _ = run(["--platform", "html", "--model", "claude-opus-5",
                      "--text", "Drafted by the model.", "--unapproved"])
        href = out.split('"')[1]
        self.assertIn("&amp;", href)
        self.assertNotIn("&t=", href)
        self.assertNotIn("&p=", href)

    def test_html_anchor_parses_as_xml(self):
        """Confluence storage format and XHTML reject a document with a bare &."""
        out, _ = run(["--platform", "html", "--unapproved", "--date", "2026-08-10"]
                     + self.ARGS)
        node = ElementTree.fromstring(out)
        self.assertEqual(node.tag, "a")
        self.assertEqual(node.text, sigil.SIGIL)
        self.assertEqual(
            node.attrib["href"],
            sigil.build_url("claude-opus-5", "Drafted by the model.",
                            unapproved=True, date="2026-08-10"),
        )

    def test_html_href_decodes_to_the_canonical_url(self):
        out, _ = run(["--platform", "html"] + self.ARGS)
        href = html.unescape(out.split('"')[1])
        self.assertEqual(
            href, sigil.build_url("claude-opus-5", "Drafted by the model.")
        )

    def test_html_escapes_markup_from_the_free_text(self):
        out, _ = run(["--platform", "html", "--model", "claude-opus-5",
                      "--text", 'He said "<b>hi</b>" & left.'])
        self.assertEqual(out.split('"')[2], ">※</a>")
        href = html.unescape(out.split('"')[1])
        self.assertEqual(params_of(href)["t"][0], 'He said "<b>hi</b>" & left.')

    def test_output_is_exactly_one_line(self):
        for platform in sigil.TARGETS:
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
        # Derived, not hardcoded: a new target is covered here the day it lands.
        for platform in [t for t in sigil.TARGETS if t not in sigil.TOOLTIP_TARGETS]:
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

    def test_html_tooltip_is_a_title_attribute(self):
        out, err = run(
            [
                "--platform", "html",
                "--model", "claude-opus-5",
                "--text", "Wording from the model, substance from the author.",
                "--tooltip",
            ]
        )
        self.assertEqual(err, "")
        node = ElementTree.fromstring(out)
        self.assertEqual(
            node.attrib["title"],
            "claude-opus-5: Wording from the model, substance from the author.",
        )

    def test_quotes_in_html_tooltip_do_not_break_the_attribute(self):
        out, _ = run(
            [
                "--platform", "html",
                "--model", "claude-opus-5",
                "--text", 'They said "hello" & left.',
                "--tooltip",
            ]
        )
        node = ElementTree.fromstring(out)
        self.assertEqual(
            node.attrib["title"], 'claude-opus-5: They said "hello" & left.'
        )
        self.assertEqual(node.text, sigil.SIGIL)

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


class TestUnapproved(unittest.TestCase):
    def test_without_flag_there_is_no_p_parameter(self):
        url = sigil.build_url("claude-opus-5", "Drafted by the model.")
        self.assertNotIn("p=", url)
        self.assertNotIn("p", params_of(url))

    def test_with_flag_p_is_agent(self):
        url = sigil.build_url("claude-opus-5", "Drafted by the model.", unapproved=True)
        self.assertEqual(params_of(url)["p"], ["agent"])

    def test_cli_flag(self):
        out, _ = run(
            [
                "--platform", "slack",
                "--model", "claude-opus-5",
                "--text", "Assembled by the agent from the ticket history.",
                "--unapproved",
            ]
        )
        self.assertIn("&p=agent", out)

    def test_former_name_is_still_accepted(self):
        """`--self-posted` predates the redefinition; callers still pass it."""
        args = [
            "--platform", "slack",
            "--model", "claude-opus-5",
            "--text", "Assembled by the agent from the ticket history.",
        ]
        old, _ = run(args + ["--self-posted"])
        new, _ = run(args + ["--unapproved"])
        self.assertEqual(old, new)
        self.assertIn("&p=agent", old)


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
            unapproved=True,
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


class TestUrlTarget(unittest.TestCase):
    """`--platform url` — the escape hatch for callers that build the link.

    Jira comments written as ADF are the motivating case: there the link is a
    mark on a text node, so the wiki wrapping `[※|URL]` has nothing to attach
    to and would show up as literal characters. Same for HTML and any API
    payload that carries href and label in separate fields.
    """

    ARGS = ["--model", "claude-opus-5", "--text", "Drafted by the model."]

    def test_prints_the_bare_url(self):
        out, _ = run(["--platform", "url"] + self.ARGS)
        self.assertTrue(out.startswith("https://zauberzeug.github.io/colophon/#"))

    def test_output_carries_no_link_syntax_and_no_sigil(self):
        out, _ = run(["--platform", "url"] + self.ARGS)
        for char in ("[", "]", "<", ">", "|", sigil.SIGIL):
            self.assertNotIn(char, out)

    def test_it_is_the_same_url_every_other_target_wraps(self):
        bare, _ = run(["--platform", "url"] + self.ARGS)
        for target in [t for t in sigil.TARGETS if t != "url"]:
            with self.subTest(target=target):
                wrapped, _ = run(["--platform", target] + self.ARGS)
                # Unescaped: the html dialect writes the same URL with `&amp;`.
                # A no-op for the dialects that need no escaping.
                self.assertIn(bare, html.unescape(wrapped))

    def test_optional_parameters_still_apply(self):
        out, _ = run(
            ["--platform", "url", "--unapproved", "--date", "2026-08-10",
             "--agent", "claude-code"] + self.ARGS
        )
        params = params_of(out)
        self.assertEqual(params["p"], ["agent"])
        self.assertEqual(params["d"], ["2026-08-10"])
        self.assertEqual(params["a"], ["claude-code"])

    def test_tooltip_warns_and_leaves_the_url_untouched(self):
        out, err = run(["--platform", "url", "--tooltip"] + self.ARGS)
        self.assertIn("--tooltip", err)
        self.assertTrue(out.startswith("https://"))
        self.assertNotIn('"', out)

    def test_no_generic_target_is_listed_as_a_platform(self):
        """PLATFORMS stays the destinations; TARGETS adds the generic ones."""
        for target in ("html", "json", "url"):
            self.assertNotIn(target, sigil.PLATFORMS)
            self.assertIn(target, sigil.TARGETS)

    def test_only_dialects_with_a_label_are_mark_targets(self):
        """`json` and `url` hand over pieces; only html joins the platforms."""
        self.assertEqual(sigil.MARK_TARGETS, sigil.PLATFORMS + ("html",))


class TestJsonTarget(unittest.TestCase):
    """`--platform json` — label and href as fields, so neither travels by memory.

    The naked-sigil incident happened because the character came from memory
    with no rule beside it. A caller building a link (Jira ADF, Block Kit, an
    insert-link dialog) used to get only the href and had to know the label;
    now both fields sit in the output, ready to copy.
    """

    ARGS = ["--model", "claude-opus-5", "--text", "Drafted by the model."]

    def test_prints_label_and_href_as_one_json_object(self):
        out, _ = run(["--platform", "json"] + self.ARGS)
        pair = json.loads(out)
        self.assertEqual(sorted(pair), ["href", "label"])
        self.assertEqual(pair["label"], sigil.SIGIL)
        self.assertEqual(
            pair["href"], sigil.build_url("claude-opus-5", "Drafted by the model.")
        )

    def test_the_label_is_the_literal_character_not_an_escape(self):
        # The output is the copy source for the label; a JSON-escaped label
        # (backslash-u-203b on screen) would put the escape sequence, not the
        # character, into the clipboard.
        out, _ = run(["--platform", "json"] + self.ARGS)
        self.assertIn(sigil.SIGIL, out)
        self.assertNotIn("\\u", out)

    def test_optional_parameters_still_apply(self):
        out, _ = run(
            ["--platform", "json", "--unapproved", "--date", "2026-08-10",
             "--agent", "claude-code"] + self.ARGS
        )
        params = params_of(json.loads(out)["href"])
        self.assertEqual(params["p"], ["agent"])
        self.assertEqual(params["d"], ["2026-08-10"])
        self.assertEqual(params["a"], ["claude-code"])


class TestComposition(unittest.TestCase):
    """`--body-file` — the message goes in, the message with the mark comes out.

    Both observed failures happened while a hand carried the mark from the
    script's output into a message. Composition removes the hand-off: the
    character never passes through the caller.
    """

    ARGS = ["--model", "claude-opus-5", "--text", "Drafted by the model."]

    def test_stdin_body_gets_the_mark_attached(self):
        mark, _ = run(["--platform", "github"] + self.ARGS)
        out, _ = run(
            ["--platform", "github", "--body-file", "-"] + self.ARGS,
            stdin="Ordered the parts.\n",
        )
        self.assertEqual(out, "Ordered the parts. " + mark)

    def test_file_body_gets_the_mark_attached(self):
        mark, _ = run(["--platform", "slack"] + self.ARGS)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write("Ordered the parts.\n")
            path = handle.name
        try:
            out, _ = run(["--platform", "slack", "--body-file", path] + self.ARGS)
        finally:
            os.unlink(path)
        self.assertEqual(out, "Ordered the parts. " + mark)

    def test_a_multi_paragraph_body_is_passed_through_unchanged(self):
        body = "First paragraph.\n\nSecond paragraph, with detail."
        mark, _ = run(["--platform", "trello"] + self.ARGS)
        out, _ = run(
            ["--platform", "trello", "--body-file", "-"] + self.ARGS, stdin=body + "\n"
        )
        self.assertEqual(out, body + " " + mark)

    def test_every_composed_message_passes_the_write_path_check(self):
        # Derived from the tuple: a new platform is covered the day it lands.
        for platform in sigil.PLATFORMS:
            with self.subTest(platform=platform):
                out, _ = run(
                    ["--platform", platform, "--body-file", "-"] + self.ARGS,
                    stdin="Ordered the parts.\n",
                )
                self.assertFalse(check.is_broken_mark(out))

    def test_assembly_targets_refuse_a_body(self):
        # html, json and url hand over pieces; there is no tail to attach to.
        for target in [t for t in sigil.TARGETS if t not in sigil.PLATFORMS]:
            with self.subTest(target=target):
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        sigil.main(["--platform", target, "--body-file", "-"] + self.ARGS)
                self.assertNotEqual(caught.exception.code, 0)

    def test_an_empty_body_is_an_error(self):
        err = io.StringIO()
        original = sys.stdin
        sys.stdin = io.StringIO("   \n")
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = sigil.main(["--platform", "github", "--body-file", "-"] + self.ARGS)
        finally:
            sys.stdin = original
        self.assertEqual(code, 1)
        self.assertIn("empty", err.getvalue())

    def test_an_unreadable_file_is_an_error_not_a_traceback(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = sigil.main(
                ["--platform", "github", "--body-file", "/nonexistent/draft.md"] + self.ARGS
            )
        self.assertEqual(code, 1)
        self.assertIn("--body-file", err.getvalue())


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
