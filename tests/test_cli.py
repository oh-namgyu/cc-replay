"""CLI tests against a fake CLAUDE_CONFIG_DIR layout; no real transcript is read."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from cc_replay import cli
from cc_replay.locator import ENV_CONFIG_DIR, find_transcripts, latest_transcript


def transcript_lines(text="hello"):
    return "\n".join([
        json.dumps({"type": "user", "uuid": "u1", "timestamp": "2026-01-01T10:00:00Z",
                    "sessionId": "s1", "cwd": "/w/demo", "version": "2.1.227",
                    "message": {"role": "user", "content": text}}),
        json.dumps({"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:00:01Z",
                    "message": {"role": "assistant", "id": "m1",
                                "content": [{"type": "text", "text": "sure"}],
                                "usage": {"input_tokens": 3, "output_tokens": 4}}}),
    ]) + "\n"


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cc-replay-cli-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.config = self.tmp / "config"
        self.projects = self.config / "projects"
        self.projects.mkdir(parents=True)
        self.previous = os.environ.get(ENV_CONFIG_DIR)
        os.environ[ENV_CONFIG_DIR] = str(self.config)
        self.addCleanup(self.restore_env)
        self.out = io.StringIO()
        self.err = io.StringIO()

    def restore_env(self):
        if self.previous is None:
            os.environ.pop(ENV_CONFIG_DIR, None)
        else:
            os.environ[ENV_CONFIG_DIR] = self.previous

    def seed(self, project, session_id, mtime, text="hello"):
        folder = self.projects / project
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (session_id + ".jsonl")
        path.write_text(transcript_lines(text), encoding="utf-8")
        os.utime(str(path), (mtime, mtime))
        return path

    def run_cli(self, argv):
        return cli.main(argv, out=self.out, err=self.err)

    def test_list_shows_recent_sessions_newest_first(self):
        self.seed("-w-alpha", "sess-old", 1_700_000_000)
        self.seed("-w-beta", "sess-new", 1_800_000_000)
        self.assertEqual(self.run_cli(["--list"]), 0)
        lines = [line for line in self.out.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertIn("sess-new", lines[0])
        self.assertIn("-w-beta", lines[0])
        self.assertIn("sess-old", lines[1])
        self.assertRegex(lines[0], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s")

    def test_list_without_sessions_exits_2(self):
        self.assertEqual(self.run_cli(["--list"]), 2)
        self.assertIn("no transcripts found", self.err.getvalue())

    def test_latest_picks_newest_mtime(self):
        self.seed("-w-alpha", "sess-old", 1_700_000_000, text="older one")
        self.seed("-w-beta", "sess-new", 1_800_000_000, text="newest one")
        output = self.tmp / "out.html"
        self.assertEqual(self.run_cli(["--latest", "-o", str(output)]), 0)
        self.assertIn("newest one", output.read_text(encoding="utf-8"))
        self.assertEqual(latest_transcript().stem, "sess-new")

    def test_latest_without_sessions_exits_2(self):
        self.assertEqual(self.run_cli(["--latest", "-o", str(self.tmp / "x.html")]), 2)
        self.assertIn("no transcripts found", self.err.getvalue())

    def test_missing_file_exits_2(self):
        code = self.run_cli([str(self.tmp / "nope.jsonl"), "-o", str(self.tmp / "x.html")])
        self.assertEqual(code, 2)
        self.assertIn("no such transcript", self.err.getvalue())

    def test_no_path_and_no_latest_is_an_argparse_error(self):
        # argparse writes its usage straight to sys.stderr before exiting.
        with contextlib.redirect_stderr(io.StringIO()) as captured:
            with self.assertRaises(SystemExit) as caught:
                self.run_cli([])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("transcript path is required", captured.getvalue())

    def test_output_written_where_told_and_absolute_path_printed(self):
        source = self.seed("-w-alpha", "sess-1", 1_700_000_000)
        output = self.tmp / "nested" / "custom.html"
        self.assertEqual(self.run_cli([str(source), "-o", str(output)]), 0)
        self.assertTrue(output.is_file())
        printed = self.out.getvalue()
        self.assertIn(str(output.resolve()), printed)
        self.assertIn("redacted", printed)
        self.assertTrue(output.read_text(encoding="utf-8").startswith("<!DOCTYPE html>"))

    def test_redaction_on_by_default_and_disabled_by_flag(self):
        # Assembled at runtime so no credential-shaped literal sits in the source.
        needle = "sk-" + "ant-" + "api03-CliSeededSecret0123"
        source = self.seed("-w-alpha", "sess-1", 1_700_000_000, text="key " + needle)
        masked_out = self.tmp / "masked.html"
        self.assertEqual(self.run_cli([str(source), "-o", str(masked_out)]), 0)
        self.assertNotIn(needle, masked_out.read_text(encoding="utf-8"))

        plain_out = self.tmp / "plain.html"
        self.assertEqual(self.run_cli([str(source), "-o", str(plain_out), "--no-redact"]), 0)
        self.assertIn(needle, plain_out.read_text(encoding="utf-8"))

    def test_max_events_is_passed_through(self):
        folder = self.projects / "-w-alpha"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "many.jsonl"
        path.write_text("".join(
            json.dumps({"type": "user", "uuid": "u%d" % index,
                        "timestamp": "2026-01-01T10:00:00Z",
                        "message": {"role": "user", "content": "msg %d" % index}}) + "\n"
            for index in range(10)), encoding="utf-8")
        output = self.tmp / "capped.html"
        self.assertEqual(self.run_cli([str(path), "-o", str(output), "--max-events", "3"]), 0)
        self.assertIn("3 steps", self.out.getvalue())

    def test_config_dir_env_is_respected(self):
        self.seed("-w-alpha", "sess-1", 1_700_000_000)
        self.assertEqual(len(find_transcripts()), 1)
        os.environ[ENV_CONFIG_DIR] = str(self.tmp / "elsewhere")
        self.assertEqual(find_transcripts(), [])


if __name__ == "__main__":
    unittest.main()
