"""Render a parsed :class:`~cc_replay.parser.Session` into one HTML document."""

import html
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import __version__
from .parser import Session
from .redactor import redact_text
from .template import CSS, JS, TEMPLATE_HTML


def _fill(template: str, values: Dict[str, str]) -> str:
    """Replace ``%%KEY%%`` placeholders in a single left-to-right pass.

    A single pass matters: substituted content (session text, titles) must never
    be rescanned for placeholders.
    """
    out = []  # type: List[str]
    cursor = 0
    while True:
        start = template.find("%%", cursor)
        if start < 0:
            break
        end = template.find("%%", start + 2)
        if end < 0:
            break
        key = template[start + 2:end]
        if key in values:
            out.append(template[cursor:start])
            out.append(values[key])
            cursor = end + 2
        else:
            out.append(template[cursor:start + 2])
            cursor = start + 2
    out.append(template[cursor:])
    return "".join(out)


def session_json(session: Session, redact: bool = True) -> str:
    """Serialize the session for embedding in a ``<script>`` block.

    When ``redact`` is set this is the second redaction gate: the patterns run
    over the serialized payload, catching anything the structural pass missed.

    Two sequences are then neutralized, both as valid JSON escapes so the
    payload still parses byte-for-byte identically:

    * ``</`` -> ``<\\/`` so no payload can close the script element early.
    * ``<!--`` -> ``<\\u0021--`` because a comment opener would put the HTML
      tokenizer into the escaped script-data state, where our own closing
      ``</script>`` stops terminating the block.
    """
    raw = json.dumps(session.to_dict(), ensure_ascii=False)
    if redact:
        raw = redact_text(raw)
    return raw.replace("</", "<\\/").replace("<!--", "<\\u0021--")


def project_name(cwd: str) -> str:
    """Short project label: the last path segment of the working directory."""
    if not cwd:
        return "unknown project"
    return os.path.basename(cwd.rstrip("/\\")) or cwd


def _when(session: Session) -> str:
    """Session span, read straight off the ISO timestamps with no timezone math.

    Kept in UTC to match the per-step clocks, so a shared replay reads the same
    for every viewer.
    """
    start, end = session.started_at, session.ended_at
    if not start:
        return "unknown date"
    span = start[:10] + " " + start[11:16]
    if end and end[:10] != start[:10]:
        span += " → " + end[:10] + " " + end[11:16]
    elif end and end[11:16] != start[11:16]:
        span += " → " + end[11:16]
    return span + " UTC"


def _moment(stamp: str) -> Optional[datetime]:
    """Parse one ISO timestamp, tolerating the trailing ``Z`` on Python 3.9."""
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration(session: Session) -> str:
    """How long the session ran, end minus start."""
    start, end = _moment(session.started_at), _moment(session.ended_at)
    if start is None or end is None:
        return "unknown"
    seconds = int((end - start).total_seconds())
    if seconds < 0:
        return "unknown"
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%dh %02dm" % (hours, minutes)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs


def redaction_badge(redact: bool) -> str:
    """Footer badge; loud when the page carries unredacted content."""
    if redact:
        return '<span class="badge badge-ok">redacted</span>'
    return '<span class="badge badge-loud">⚠ unredacted</span>'


def _notes(session: Session) -> str:
    """Extra header chips for anything the reader should not silently miss."""
    counts = session.counts
    chips = []  # type: List[str]
    for value, label in (
        (counts.get("errors", 0), "tool errors"),
        (counts.get("unknown", 0), "unhandled events"),
        (session.malformed_lines, "malformed lines"),
        (session.dropped_steps, "older steps hidden"),
    ):
        if value:
            chips.append('<span class="stat note"><b>%d</b> %s</span>' % (value, label))
    return "\n    ".join(chips)


def render(session: Session, redact: bool = True) -> str:
    """Build the complete, self-contained HTML replay document."""
    counts = session.counts
    tokens = session.tokens
    title = session.title.strip() or "Claude Code session"
    values = {
        "CSS": CSS,
        "JS": JS,
        "VERSION": html.escape(__version__),
        "TITLE": html.escape(title),
        "PROJECT": html.escape(project_name(session.cwd)),
        "DATE": html.escape(_when(session)),
        "BRANCH": html.escape(session.git_branch or "no branch"),
        "SESSION_ID": html.escape(session.session_id[:8] or "no id"),
        "CC_VERSION": html.escape(session.version or "unknown"),
        "TURNS": "{:,}".format(counts.get("turns", 0)),
        "TOOLS": "{:,}".format(counts.get("tool_calls", 0)),
        "DURATION": html.escape(duration(session)),
        "TOKENS_IN": "{:,}".format(tokens.get("input", 0)),
        "TOKENS_OUT": "{:,}".format(tokens.get("output", 0)),
        "TOKENS_CACHE_READ": "{:,}".format(tokens.get("cache_read", 0)),
        "TOKENS_CACHE_WRITE": "{:,}".format(tokens.get("cache_creation", 0)),
        "GENERATED": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "REDACTION_BADGE": redaction_badge(redact),
        "NOTES": _notes(session),
        "SESSION_JSON": session_json(session, redact=redact),
    }
    return _fill(TEMPLATE_HTML, values)
