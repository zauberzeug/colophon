#!/usr/bin/env python3
"""Claude Code PreToolUse hook: refuse to send a colophon that is broken.

Reads the hook payload on stdin, pulls every human-visible string out of
``tool_input``, and denies the call when one of them carries a broken mark.
The denial reason goes back to the model, which can fix the text and repeat the
call — the guard costs a round trip and never loses the message.

Why a hook and not a rule in the skill: the rule was already in the skill, and
it did not hold. The agent that shipped a bare sigil had never opened the file
— it knew the character from an always-loaded routing line and nothing else.
A rule that only exists as prose fires only when someone reads the prose. What
is mechanically decidable belongs where it cannot be skipped.

Scope. The matcher covers ``Bash`` and MCP tools, which is where outgoing text
lives for this plugin's audience: ``gh issue comment -b "…"``, a ``curl`` to the
Jira or Slack API, an MCP server that posts. It deliberately does not cover
``Write``/``Edit``: those are local files, where a marker is content rather than
a message — including the documentation of this very failure mode.

An integration with its own tool layer (an agent gateway, a bot framework)
should call ``find_violations`` from ``skills/colophon/scripts/check.py`` at its
own write path instead. The rule is the reusable part; this file is one wiring
of it.
"""

import json
import os
import re
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "colophon", "scripts"),
)

from check import explain, find_violations  # noqa: E402

# Quoted argument bodies inside a shell command. A trailing mark sits at the end
# of the MESSAGE, not at the end of the command line, so the message has to be
# lifted out before the position rule can see it.
_QUOTED = re.compile(r"'([^']*)'|\"((?:[^\"\\]|\\.)*)\"", re.DOTALL)


def candidate_texts(tool_name, tool_input):
    """Every string a human might end up reading, longest-first."""
    texts = []

    def walk(value):
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(tool_input)

    if tool_name == "Bash":
        for text in list(texts):
            for match in _QUOTED.finditer(text):
                quoted = match.group(1) if match.group(1) is not None else match.group(2)
                if quoted:
                    texts.append(quoted)

    return texts


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # fail open: a guard must never take down the tool layer

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    for text in candidate_texts(tool_name, tool_input):
        violations = find_violations(text)
        if not violations:
            continue
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Colophon guard: %s [%s]"
                    % (explain(violations), ", ".join(violations)),
                }
            },
            sys.stdout,
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
