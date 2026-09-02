"""Renderer tests: the page must be complete, self-contained and injection-safe."""

import json
import re
import unittest

from cc_replay import __version__
from cc_replay.parser import Session, Step
from cc_replay.renderer import render, session_json


def demo_session(steps=None, **overrides):
    session = Session(
        title="Demo session",
        session_id="abcdef1234",
        version="2.1.227",
        cwd="/work/demo-project",
        git_branch="main",
        started_at="2026-01-01T10:00:00Z",
        ended_at="2026-01-01T11:30:00Z",
        steps=steps if steps is not None else default_steps(),
        meta_counts={"attachment": 3},
        counts={"turns": 4, "user": 2, "assistant": 2, "tool_calls": 2, "errors": 1,
                "unknown": 1, "system": 0, "thinking": 1, "subagent": 1,
                "pending": 1, "malformed": 0},
        tokens={"input": 1234, "output": 5678, "cache_read": 90, "cache_creation": 12},
    )
    for key, value in overrides.items():
        setattr(session, key, value)
    return session


def default_steps():
    return [
        Step(kind="user", timestamp="2026-01-01T10:00:00Z", text="please list files"),
        Step(kind="assistant", timestamp="2026-01-01T10:00:01Z", text="on it"),
        Step(kind="thinking", timestamp="2026-01-01T10:00:02Z", text="considering"),
        Step(kind="tool_call", timestamp="2026-01-01T10:00:03Z", tool_name="Bash",
             tool_use_id="toolu_1", tool_input='{"command": "ls"}', result="a\nb"),
        Step(kind="tool_call", timestamp="2026-01-01T10:00:04Z", tool_name="Read",
             tool_use_id="toolu_2", tool_input='{"path": "x"}', result="nope",
             is_error=True),
        Step(kind="subagent", timestamp="2026-01-01T10:00:05Z", text="subagent",
             children=[Step(kind="assistant", text="child work")]),
        Step(kind="unknown", timestamp="2026-01-01T10:00:06Z", subtype="mystery-type",
             raw='{"type": "mystery-type"}'),
    ]


class RendererTestCase(unittest.TestCase):
    def test_document_shell(self):
        page = render(demo_session())
        self.assertTrue(page.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn('<script type="application/json" id="session-data">', page)
        self.assertIn("</html>", page)
        self.assertNotIn("%%", page)

    def test_header_shows_title_project_and_stats(self):
        page = render(demo_session())
        self.assertIn("Demo session", page)
        self.assertIn("demo-project", page)
        self.assertIn("2026-01-01 10:00 → 11:30 UTC", page)
        self.assertIn("<b>4</b> turns", page)
        self.assertIn("<b>2</b> tool calls", page)
        self.assertIn("main", page)

    def test_header_token_line_and_duration(self):
        page = render(demo_session())
        self.assertIn("<b>1,234</b> in", page)
        self.assertIn("<b>5,678</b> out", page)
        self.assertIn("<b>90</b> read", page)
        self.assertIn("<b>12</b> written", page)
        self.assertIn("<b>1h 30m</b> long", page)

    def test_duration_formats(self):
        short = render(demo_session(started_at="2026-01-01T10:00:00Z",
                                    ended_at="2026-01-01T10:00:42Z"))
        self.assertIn("<b>42s</b> long", short)
        medium = render(demo_session(started_at="2026-01-01T10:00:00Z",
                                     ended_at="2026-01-01T10:07:05Z"))
        self.assertIn("<b>7m 05s</b> long", medium)
        unknown = render(demo_session(started_at="", ended_at=""))
        self.assertIn("<b>unknown</b> long", unknown)

    def test_notes_surface_errors_and_unknowns(self):
        page = render(demo_session())
        self.assertIn("<b>1</b> tool errors", page)
        self.assertIn("<b>1</b> unhandled events", page)
        clean = render(demo_session(counts={"turns": 1, "tool_calls": 0}, malformed_lines=0))
        self.assertNotIn("tool errors", clean)

    def test_tool_rows_are_collapsed_details(self):
        page = render(demo_session())
        self.assertIn('<details class="', page)
        self.assertIn("tool-row", page)
        self.assertIn("tool-name", page)
        self.assertIn("unknown-row", page)
        self.assertIn("subagent", page)

    def test_script_close_in_text_is_escaped(self):
        hostile = '</script><img onerror="alert(1)"> and </div>'
        steps = [Step(kind="user", timestamp="2026-01-01T10:00:00Z", text=hostile)]
        page = render(demo_session(steps=steps))
        block = page.split('id="session-data">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("</script", block)
        self.assertNotIn("</div", block)
        self.assertIn("<\\/script", block)
        self.assertEqual(json.loads(block)["steps"][0]["text"], hostile)

    def test_title_is_html_escaped(self):
        page = render(demo_session(title='<img src=x onerror="boom">'))
        markup = page.split('id="session-data">', 1)[0]
        self.assertNotIn("<img src=x", markup)
        self.assertIn("&lt;img src=x", markup)
        self.assertIn("&quot;boom&quot;", markup)

    def test_comment_opener_in_text_is_neutralized(self):
        # "<!--" would switch the tokenizer into escaped script-data state,
        # where the page's own </script> no longer closes the data block.
        hostile = "<!-- <script>steal()</script> -->"
        steps = [Step(kind="user", timestamp="2026-01-01T10:00:00Z", text=hostile)]
        page = render(demo_session(steps=steps))
        block = page.split('id="session-data">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<!--", block)
        self.assertNotIn("</script", block)
        self.assertEqual(json.loads(block)["steps"][0]["text"], hostile)

    def test_session_json_round_trips(self):
        session = demo_session()
        data = json.loads(session_json(session).replace("<\\/", "</"))
        self.assertEqual(data["session_id"], "abcdef1234")
        self.assertEqual(len(data["steps"]), len(session.steps))
        self.assertEqual(data["steps"][5]["children"][0]["text"], "child work")

    def test_title_and_inline_favicon(self):
        page = render(demo_session())
        self.assertIn("<title>cc-replay &middot; Demo session</title>", page)
        self.assertIn('<link rel="icon" href="data:image/svg+xml,', page)
        # The icon is inline, so the browser never requests /favicon.ico.
        self.assertNotIn(".ico", page)

    def test_no_external_resources(self):
        page = render(demo_session())
        # The favicon is an inline SVG data URI. Its xmlns is a namespace
        # identifier that browsers never fetch, so it is the one permitted
        # URL-shaped string; everything else must be free of them.
        icon = re.search(r'<link rel="icon"[^>]*>', page)
        self.assertIsNotNone(icon)
        body = page.replace(icon.group(0), "")
        self.assertNotIn("http://", body)
        self.assertNotIn("https://", body)
        self.assertNotIn("//cdn", page)
        # Only the static markup is scanned: the script bodies legitimately
        # contain an href pattern used to build markdown links at runtime.
        for chunk in re.split(r"<script[^>]*>.*?</script>", body, flags=re.S):
            for attribute in ("src", "href"):
                for value in re.findall(r'\b%s\s*=\s*"([^"]*)"' % attribute, chunk):
                    self.assertTrue(value.startswith("#"), "off-page resource: " + value)
        for banned in ("fetch(", "XMLHttpRequest", "WebSocket", "@import", "importScripts"):
            self.assertNotIn(banned, page)

    def test_markdown_links_are_restricted_to_web_urls(self):
        page = render(demo_session())
        self.assertIn('rel="noopener noreferrer"', page)
        self.assertIn('target="_blank"', page)
        # The link rule only ever fires on an http(s) prefix, and the
        # lookbehind keeps image syntax out so images can never load.
        self.assertIn("https?:", page)
        self.assertIn("(?<!!)", page)

    def test_playback_bar_present(self):
        page = render(demo_session())
        for marker in ('id="playbar"', 'id="pb-prev"', 'id="pb-play"', 'id="pb-next"',
                       'id="pb-range"', 'id="pb-count"', 'type="range"'):
            self.assertIn(marker, page)
        self.assertIn("future", page)

    def test_footer_reports_version_and_generation_time(self):
        page = render(demo_session())
        self.assertIn("Generated by cc-replay", page)
        self.assertIn(__version__, page)
        self.assertRegex(page, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")

    def test_redaction_badge_reflects_the_flag(self):
        self.assertIn("redacted", render(demo_session()))
        self.assertNotIn("unredacted", render(demo_session()))
        plain = render(demo_session(), redact=False)
        self.assertIn("unredacted", plain)
        self.assertIn("badge-loud", plain)

    def test_markdown_input_cannot_inject_markup(self):
        hostile = ("# heading\n\n```js\n<script>steal()</script>\n```\n\n"
                   "text with <script>alert(1)</script> and [x](javascript:evil)")
        steps = [Step(kind="assistant", timestamp="2026-01-01T10:00:00Z", text=hostile)]
        page = render(demo_session(steps=steps))
        head, rest = page.split('id="session-data">', 1)
        block, tail = rest.split("</script>", 1)
        # The payload keeps the text verbatim (an opening "<script" is inert
        # text here; only "</script" could end the block, and that is escaped).
        self.assertNotIn("</script", block)
        self.assertEqual(json.loads(block)["steps"][0]["text"], hostile)
        # Outside the data block the only script elements are the template's
        # own two, so no user content became a live element.
        self.assertEqual((head + tail).count("<script"), 2)

    def test_markdown_helpers_are_named_functions(self):
        page = render(demo_session())
        for name in ("function markdown(", "function inlineMd(", "function mdBlocks("):
            self.assertIn(name, page)

    def test_performance_hints_present(self):
        page = render(demo_session())
        self.assertIn("content-visibility: auto", page)
        self.assertIn("contain-intrinsic-size: auto 120px", page)

    def test_empty_session_still_renders(self):
        page = render(Session())
        self.assertTrue(page.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn("Claude Code session", page)
        self.assertIn("unknown date", page)
        self.assertIn("No renderable steps", page)
        self.assertIn('id="playbar"', page)
        self.assertNotIn("%%", page)
        block = page.split('id="session-data">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(block)["steps"], [])

    def test_hostile_payloads_never_reach_markup(self):
        payloads = [
            "<img src=x onerror=alert(1)>",
            '"><scr' + 'ipt>alert(1)</scr' + 'ipt>',
            "<iframe srcdoc=hi>",
            "<svg onload=alert(1)>",
            "javascript:alert(1)",
            "' onmouseover='alert(1)",
        ]
        blob = " ".join(payloads)
        steps = [
            Step(kind="user", text=blob),
            Step(kind="assistant", text="[link](javascript:alert(1)) " + blob),
            Step(kind="tool_call", tool_name=blob, tool_use_id="toolu_x",
                 tool_input=json.dumps({"cmd": blob}), result=blob),
            Step(kind="unknown", subtype=blob, raw=json.dumps({"x": blob})),
        ]
        html_page = render(demo_session(steps=steps, title=blob))
        # Strip the inert JSON data block; everything else is live markup.
        live = re.sub(
            r'<script type="application/json" id="session-data">.*?</script>',
            "", html_page, flags=re.S)
        # Escaped payloads legitimately survive as inert text (&lt;img ...);
        # only ACTIVE markup forms are forbidden in live HTML.
        for needle in ("<img", "<iframe", '<svg onload',
                       'href="javascript:', "' onmouseover='"):
            self.assertNotIn(needle, live)
        # The JSON block itself must stay parseable (payloads inert as data).
        parsed = json.loads(session_json(demo_session(steps=steps, title=blob)))
        self.assertEqual(parsed["steps"][0]["text"], blob)


if __name__ == "__main__":
    unittest.main()