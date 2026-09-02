"""Parser tests. Fixtures are synthetic: no real transcript is ever read."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cc_replay.parser import MAX_TEXT_CHARS, parse_transcript


def user_text(uuid, text, **extra):
    event = {"type": "user", "uuid": uuid, "timestamp": "2026-01-01T10:00:00Z",
             "message": {"role": "user", "content": text}}
    event.update(extra)
    return event


def user_blocks(uuid, blocks, **extra):
    event = {"type": "user", "uuid": uuid, "timestamp": "2026-01-01T10:00:01Z",
             "message": {"role": "user", "content": blocks}}
    event.update(extra)
    return event


def assistant(uuid, blocks, usage=None, message_id=None, **extra):
    message = {"role": "assistant", "id": message_id or ("msg_" + uuid), "content": blocks}
    if usage is not None:
        message["usage"] = usage
    event = {"type": "assistant", "uuid": uuid, "timestamp": "2026-01-01T10:00:02Z",
             "sessionId": "sess-1", "version": "2.1.227", "cwd": "/w/demo",
             "gitBranch": "main", "message": message}
    event.update(extra)
    return event


def tool_use(use_id, name="Bash", command="ls"):
    return {"type": "tool_use", "id": use_id, "name": name, "input": {"command": command}}


def tool_result(use_id, content, is_error=False):
    return {"type": "tool_result", "tool_use_id": use_id,
            "content": content, "is_error": is_error}


class ParserTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cc-replay-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def write(self, events, raw_tail=None, name="t.jsonl"):
        """Write a transcript; ``raw_tail`` is appended verbatim (no newline)."""
        path = self.tmp / name
        lines = [json.dumps(event) for event in events]
        text = "".join(line + "\n" for line in lines)
        if raw_tail is not None:
            text += raw_tail
        path.write_text(text, encoding="utf-8")
        return path

    def kinds(self, session):
        return [step.kind for step in session.steps]

    def test_user_string_content(self):
        session = parse_transcript(self.write([user_text("u1", "hello there")]))
        self.assertEqual(self.kinds(session), ["user"])
        self.assertEqual(session.steps[0].text, "hello there")
        self.assertEqual(session.counts["user"], 1)

    def test_user_block_content(self):
        events = [user_blocks("u1", [{"type": "text", "text": "block form"}])]
        session = parse_transcript(self.write(events))
        self.assertEqual(session.steps[0].text, "block form")

    def test_assistant_text_and_tool_use(self):
        events = [assistant("a1", [{"type": "text", "text": "on it"}, tool_use("toolu_1")])]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["assistant", "tool_call"])
        call = session.steps[1]
        self.assertEqual(call.tool_name, "Bash")
        self.assertIn("ls", call.tool_input)
        self.assertEqual(session.session_id, "sess-1")
        self.assertEqual(session.version, "2.1.227")
        self.assertEqual(session.git_branch, "main")

    def test_thinking_block(self):
        events = [assistant("a1", [{"type": "thinking", "thinking": "hmm", "signature": "x"}])]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["thinking"])
        self.assertEqual(session.steps[0].text, "hmm")

    def test_tool_result_pairing(self):
        events = [assistant("a1", [tool_use("toolu_1")]),
                  user_blocks("u1", [tool_result("toolu_1", "file-a\nfile-b")])]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["tool_call"])
        call = session.steps[0]
        self.assertEqual(call.result, "file-a\nfile-b")
        self.assertFalse(call.is_error)
        self.assertFalse(call.pending)

    def test_tool_result_block_list_and_error(self):
        blocks = [{"type": "text", "text": "boom"}, {"type": "text", "text": "trace"}]
        events = [assistant("a1", [tool_use("toolu_1")]),
                  user_blocks("u1", [tool_result("toolu_1", blocks, is_error=True)])]
        session = parse_transcript(self.write(events))
        call = session.steps[0]
        self.assertEqual(call.result, "boom\ntrace")
        self.assertTrue(call.is_error)
        self.assertEqual(session.counts["errors"], 1)

    def test_missing_result_is_pending(self):
        session = parse_transcript(self.write([assistant("a1", [tool_use("toolu_9")])]))
        call = session.steps[0]
        self.assertTrue(call.pending)
        self.assertEqual(call.result, "")
        self.assertEqual(session.counts["pending"], 1)

    def test_unknown_event_type_kept_raw(self):
        events = [{"type": "some-future-event", "uuid": "x1", "payload": {"a": 1}}]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["unknown"])
        step = session.steps[0]
        self.assertEqual(step.subtype, "some-future-event")
        self.assertIn("some-future-event", step.raw)
        self.assertEqual(session.counts["unknown"], 1)

    def test_file_history_delta_is_meta(self):
        events = [{"type": "file-history-delta", "uuid": "x1", "payload": {"a": 1}},
                  user_text("u1", "hi")]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["user"])
        self.assertEqual(session.meta_counts["file-history-delta"], 1)
        self.assertEqual(session.counts["unknown"], 0)

    def test_malformed_line_counted_and_skipped(self):
        path = self.write([user_text("u1", "before")])
        with open(str(path), "a", encoding="utf-8") as handle:
            handle.write("{not json at all\n")
            handle.write(json.dumps(user_text("u2", "after")) + "\n")
        session = parse_transcript(path)
        self.assertEqual(self.kinds(session), ["user", "user"])
        self.assertEqual(session.malformed_lines, 1)
        self.assertEqual(session.counts["malformed"], 1)

    def test_truncated_final_line(self):
        tail = json.dumps(user_text("u2", "cut off"))[:40]
        session = parse_transcript(self.write([user_text("u1", "ok")], raw_tail=tail))
        self.assertEqual(self.kinds(session), ["user"])
        self.assertEqual(session.malformed_lines, 1)

    def test_system_event(self):
        events = [{"type": "system", "uuid": "s1", "subtype": "hook",
                   "content": "hook ran", "level": "info"}]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["system"])
        self.assertEqual(session.steps[0].subtype, "hook")
        self.assertEqual(session.steps[0].text, "hook ran")

    def test_sidechain_attached_via_source_tool_use_id(self):
        events = [
            assistant("a1", [tool_use("toolu_task", name="Agent")]),
            assistant("a2", [{"type": "text", "text": "sub work"}],
                      isSidechain=True, sourceToolUseID="toolu_task"),
            user_blocks("u1", [tool_result("toolu_task", "done")]),
            assistant("a3", [{"type": "text", "text": "back on main"}]),
        ]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["tool_call", "assistant"])
        children = session.steps[0].children
        self.assertEqual([child.text for child in children], ["sub work"])
        self.assertEqual(session.steps[0].result, "done")
        self.assertEqual(session.counts["assistant"], 2)

    def test_orphan_sidechain_becomes_subagent_group(self):
        events = [
            user_text("u1", "start"),
            assistant("a1", [{"type": "text", "text": "sub one"}], isSidechain=True),
            assistant("a2", [{"type": "text", "text": "sub two"}], isSidechain=True),
            user_text("u2", "end"),
        ]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["user", "subagent", "user"])
        group = session.steps[1]
        self.assertEqual([child.text for child in group.children], ["sub one", "sub two"])
        self.assertEqual(session.counts["subagent"], 1)

    def test_meta_types_tallied_not_rendered(self):
        events = [
            {"type": "ai-title", "aiTitle": "Refactor the parser"},
            {"type": "mode", "mode": "default"},
            {"type": "attachment", "attachment": {"k": 1}},
            {"type": "queue-operation", "operation": "add"},
            user_text("u1", "hi"),
        ]
        session = parse_transcript(self.write(events))
        self.assertEqual(self.kinds(session), ["user"])
        self.assertEqual(session.meta_counts["ai-title"], 1)
        self.assertEqual(session.meta_counts["attachment"], 1)
        self.assertEqual(session.title, "Refactor the parser")

    def test_title_falls_back_to_first_user_then_filename(self):
        session = parse_transcript(self.write([user_text("u1", "first words here")]))
        self.assertEqual(session.title, "first words here")
        empty = parse_transcript(self.write([{"type": "mode"}], name="named.jsonl"))
        self.assertEqual(empty.title, "named")

    def test_meta_user_event_flagged(self):
        events = [user_text("u1", "caveat text", isMeta=True), user_text("u2", "real")]
        session = parse_transcript(self.write(events))
        self.assertTrue(session.steps[0].is_meta)
        self.assertEqual(session.title, "real")

    def test_usage_summed_once_per_message_id(self):
        usage = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100,
                 "cache_creation_input_tokens": 7, "service_tier": "standard"}
        events = [
            assistant("a1", [{"type": "text", "text": "one"}], usage=usage, message_id="msg_A"),
            # Streamed blocks repeat one message id and its usage: count it once.
            assistant("a2", [tool_use("toolu_1")], usage=usage, message_id="msg_A"),
            assistant("a3", [{"type": "text", "text": "two"}], usage=usage, message_id="msg_B"),
        ]
        session = parse_transcript(self.write(events))
        self.assertEqual(session.tokens["input"], 20)
        self.assertEqual(session.tokens["output"], 10)
        self.assertEqual(session.tokens["cache_read"], 200)
        self.assertEqual(session.tokens["cache_creation"], 14)

    def test_timestamps_and_turn_counts(self):
        events = [user_text("u1", "a"), assistant("a1", [{"type": "text", "text": "b"}])]
        session = parse_transcript(self.write(events))
        self.assertEqual(session.started_at, "2026-01-01T10:00:00Z")
        self.assertEqual(session.ended_at, "2026-01-01T10:00:02Z")
        self.assertEqual(session.counts["turns"], 2)

    def test_long_payload_truncated(self):
        huge = "x" * (MAX_TEXT_CHARS + 5000)
        events = [assistant("a1", [tool_use("toolu_1")]),
                  user_blocks("u1", [tool_result("toolu_1", huge)]),
                  user_text("u2", huge)]
        session = parse_transcript(self.write(events))
        call, message = session.steps[0], session.steps[1]
        self.assertLess(len(call.result), len(huge))
        self.assertIn("[truncated 5000 chars]", call.result)
        self.assertIn("[truncated 5000 chars]", message.text)

    def test_many_lines_truncated(self):
        many = "\n".join(str(number) for number in range(1500))
        session = parse_transcript(self.write([user_text("u1", many)]))
        text = session.steps[0].text
        self.assertIn("[truncated", text)
        self.assertLess(len(text.split("\n")), 1010)

    def test_max_events_drops_from_the_front(self):
        events = [user_text("u%d" % number, "msg %d" % number) for number in range(10)]
        session = parse_transcript(self.write(events), max_events=4)
        self.assertEqual(len(session.steps), 4)
        self.assertEqual(session.dropped_steps, 6)
        self.assertEqual(session.steps[0].text, "msg 6")
        self.assertEqual(session.steps[-1].text, "msg 9")

    def test_empty_and_blank_lines(self):
        path = self.tmp / "blank.jsonl"
        path.write_text("\n\n", encoding="utf-8")
        session = parse_transcript(path)
        self.assertEqual(session.steps, [])
        self.assertEqual(session.malformed_lines, 0)


if __name__ == "__main__":
    unittest.main()
