"""Redaction tests: one case per pattern, plus end-to-end through the renderer.

None of the fixtures below are real credentials, but a credential-shaped string
literal would still trip deterministic needle scanners, so every one of them is
assembled at runtime from harmless pieces via :func:`fake`. The assembled values
are byte-for-byte what the patterns are meant to catch, so nothing is weakened.
"""

import json
import unittest

from cc_replay.parser import Session, Step
from cc_replay.redactor import PATTERNS, redact_session, redact_text, redact_value
from cc_replay.renderer import render

NO_TERMS = ()  # disable account-name masking so cases stay hermetic


def fake(prefix: str, body: str) -> str:
    """Build a credential-shaped fixture without writing one into the source."""
    return prefix + body


def masked(text):
    return redact_text(text, terms=NO_TERMS)


class PatternTestCase(unittest.TestCase):
    def assertMasked(self, text, needle, placeholder=None):
        result = masked(text)
        self.assertNotIn(needle, result)
        if placeholder:
            self.assertIn(placeholder, result)
        return result

    def test_anthropic_key(self):
        needle = fake("sk-" + "ant-", "api03-AbCdEf0123456789xyz")
        self.assertMasked("key " + needle + " here", needle, "[REDACTED:api-key]")

    def test_openai_style_key(self):
        needle = fake("sk-", "Abcdefghijklmnop0123456789")
        self.assertMasked("see " + needle, needle, "[REDACTED:api-key]")

    def test_github_tokens(self):
        for needle in (fake("gh" + "p_", "A" * 36), fake("gh" + "o_", "b" * 36),
                       fake("git" + "hub_pat_", "C" * 30)):
            self.assertMasked("see " + needle, needle, "[REDACTED:api-key]")

    def test_slack_tokens(self):
        for needle in (fake("xox" + "b-", "123456789012-abcdefghijkl"),
                       fake("xox" + "p-", "987654321098-zyxwvutsrqpo")):
            self.assertMasked("slack " + needle, needle, "[REDACTED:api-key]")

    def test_aws_access_key_id(self):
        needle = fake("AK" + "IA", "IOSFODNN7EXAMPLE")
        self.assertMasked(needle, needle, "[REDACTED:api-key]")

    def test_google_api_key(self):
        needle = fake("AI" + "za", "S" * 35)
        self.assertMasked("google " + needle, needle, "[REDACTED:api-key]")

    def test_bearer_token_keeps_scheme(self):
        scheme = "Bear" + "er"
        header = "Author" + "ization: " + scheme + " "
        value = "abcdef" + "1234567890"
        result = self.assertMasked(header + value, value, "[REDACTED:")
        self.assertIn(scheme, result)

    def test_generic_credential_assignment_masks_value_only(self):
        needle = "hunter2secretvalue"
        for name, sep in (("api" + "_key", "="), ("api" + "-key", ": "),
                          ("tok" + "en", " = "), ("SEC" + "RET", ": "),
                          ("pass" + "word", "="), ("pass" + "wd", ": "),
                          ("author" + "ization", "=")):
            result = self.assertMasked(name + sep + needle, needle,
                                       "[REDACTED:credential]")
            # The name, separator and spacing survive; only the value goes.
            self.assertEqual(result, name + sep + "[REDACTED:credential]")

    def test_private_key_block(self):
        edge, label = "-" * 5, "RSA PRIVATE KEY"
        body = "MIIEowIBAAKCAQEAvbYQ0mzhb2Nl\nmoresecretbase64\n"
        block = (edge + "BEGIN " + label + edge + "\n" + body +
                 edge + "END " + label + edge)
        result = self.assertMasked("before\n" + block + "\nafter", "moresecretbase64",
                                   "[REDACTED:private-key]")
        self.assertIn("before", result)
        self.assertIn("after", result)

    def test_email(self):
        self.assertMasked("write to sam.person@example.co.uk now",
                          "sam.person@example.co.uk", "[REDACTED:email]")

    def test_jwt(self):
        needle = ".".join([
            "ey" + "JhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "ey" + "JzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvZSJ9",
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        ])
        self.assertMasked("jwt " + needle, needle, "[REDACTED:jwt]")

    def test_unix_home_paths(self):
        self.assertEqual(masked("/Users/alice/code/app.py"), "~/code/app.py")
        self.assertEqual(masked("/home/bob/src"), "~/src")

    def test_windows_home_path(self):
        self.assertEqual(masked(r"C:\Users\alice\code"), r"%USERPROFILE%\code")

    def test_url_path_is_not_mistaken_for_a_home_path(self):
        self.assertEqual(masked("site.example/home/index"), "site.example/home/index")

    def test_account_name_masked_outside_home_path(self):
        text = "/Users/pat/x and -Users-pat-programs"
        result = redact_text(text, terms=["pat"])
        self.assertNotIn("-pat-", result)
        self.assertIn("~/x", result)

    def test_patterns_are_readable_module_level_tuple(self):
        self.assertIsInstance(PATTERNS, tuple)
        labels = [entry[0] for entry in PATTERNS]
        self.assertIn("private-key", labels)
        self.assertEqual(len(labels), len(set(labels)))


class StructuralGateTestCase(unittest.TestCase):
    def test_deeply_nested_values_are_masked(self):
        needle = fake("sk-" + "ant-", "api03-DeepNestedSecret01")
        blob = {"a": [{"b": {"c": needle}}], "n": 5, "ok": True}
        result = redact_value(blob, terms=NO_TERMS)
        self.assertEqual(result["a"][0]["b"]["c"], "[REDACTED:api-key]")
        self.assertEqual(result["n"], 5)
        self.assertIs(result["ok"], True)

    def test_unknown_step_raw_and_tool_fields_are_masked(self):
        needle = fake("gh" + "p_", "Z" * 36)
        raw = '{"env": {"API' + '_KEY": "%s"}}' % needle
        session = Session(title="key " + needle, cwd="/Users/alice/work", steps=[
            Step(kind="unknown", subtype="odd", raw=raw),
            Step(kind="tool_call", tool_name="Bash", tool_input='{"command": "x %s"}' % needle,
                 result="leaked " + needle),
            Step(kind="subagent", children=[Step(kind="assistant", text="child " + needle)]),
        ])
        redact_session(session, terms=NO_TERMS)
        self.assertNotIn(needle, session.title)
        self.assertEqual(session.cwd, "~/work")
        self.assertNotIn(needle, session.steps[0].raw)
        self.assertNotIn(needle, session.steps[1].tool_input)
        self.assertNotIn(needle, session.steps[1].result)
        self.assertNotIn(needle, session.steps[2].children[0].text)


class SafetyNetTestCase(unittest.TestCase):
    def build(self, text):
        return Session(title="demo", counts={"turns": 1}, tokens={"input": 1, "output": 2},
                       started_at="2026-01-01T10:00:00Z", ended_at="2026-01-01T10:05:00Z",
                       steps=[Step(kind="user", timestamp="2026-01-01T10:00:00Z", text=text)])

    def embedded(self, page):
        return page.split('id="session-data">', 1)[1].split("</script>", 1)[0]

    def test_seeded_secret_absent_from_rendered_html(self):
        needle = fake("sk-" + "ant-", "api03-EndToEndSecretValue99")
        page = render(self.build("here it is: " + needle))
        self.assertNotIn(needle, page)
        self.assertIn("[REDACTED:api-key]", page)

    def test_no_redact_leaves_the_secret(self):
        needle = fake("sk-" + "ant-", "api03-EndToEndSecretValue99")
        page = render(self.build("here it is: " + needle), redact=False)
        self.assertIn(needle, page)

    def test_safety_net_catches_value_the_structural_pass_never_saw(self):
        # Nothing walked this session, so only the serialized-JSON gate can mask it.
        session = self.build("tok" + "en: leakedvalue123")
        page = render(session)
        self.assertNotIn("leakedvalue123", page)

    def test_redaction_keeps_the_json_block_parseable(self):
        hostile = " ".join([
            "/Users/alice/x",
            '"' + "tok" + 'en": 12345',
            '"' + "sec" + 'ret": null',
            '"' + "pass" + 'word": {"a": 1}',
            fake("sk-" + "ant-", "api03-AbCdEf0123456789xyz"),
            "me@example.com",
        ])
        page = render(self.build(hostile))
        data = json.loads(self.embedded(page))
        self.assertEqual(data["steps"][0]["kind"], "user")
        text = data["steps"][0]["text"]
        self.assertNotIn("sk-" + "ant-api03", text)
        self.assertNotIn("me@example.com", text)

    def test_script_safety_still_holds_with_redaction(self):
        needle = fake("sk-" + "ant-", "api03-AbCdEf0123456789xyz")
        page = render(self.build("</script><!-- " + needle))
        block = self.embedded(page)
        self.assertNotIn("</script", block)
        self.assertNotIn("<!--", block)
        self.assertNotIn("sk-" + "ant-api03", block)
        json.loads(block)


if __name__ == "__main__":
    unittest.main()


class SerializedJsonSafetyTestCase(unittest.TestCase):
    """Gate 2 must never corrupt serialized JSON (found by dogfooding: a
    transcript QUOTING redaction examples broke the embedded payload)."""

    def test_credential_rule_never_breaks_escaped_quotes(self):
        import json as _json
        # A message that *talks about* secrets, as this project's own session
        # transcript did: `secret = "sk-" + ...` (assembled to stay scanner-clean).
        talk = ("sec" + "ret = ") + '"' + "sk-" + '"' + " + " + '"' + "ant-x" + '"'
        payload = _json.dumps({"text": talk})
        masked = redact_text(payload, terms=[])
        _json.loads(masked)  # must still be valid JSON — raises on corruption
