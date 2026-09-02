"""Command line interface for cc-replay."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import IO, List, Optional

from . import __version__
from .locator import find_transcripts, latest_transcript, projects_dir
from .parser import DEFAULT_MAX_EVENTS, parse_transcript
from .redactor import redact_session
from .renderer import render

LIST_LIMIT = 20
DEFAULT_OUTPUT = "replay.html"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cc-replay",
        description="Turn a Claude Code transcript into a self-contained HTML replay.")
    parser.add_argument("path", nargs="?", type=Path, default=None,
                        help="path to a .jsonl transcript")
    parser.add_argument("--latest", action="store_true",
                        help="use the most recently modified transcript")
    parser.add_argument("--list", action="store_true",
                        help="list the %d most recent sessions and exit" % LIST_LIMIT)
    parser.add_argument("-o", "--output", type=Path, default=Path(DEFAULT_OUTPUT),
                        help="output HTML file (default: %s)" % DEFAULT_OUTPUT)
    parser.add_argument("--no-redact", action="store_true",
                        help="do not mask secrets and home paths (redaction is on by default)")
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS,
                        metavar="N", help="keep only the last N steps (default: %(default)s)")
    parser.add_argument("--version", action="version", version="cc-replay " + __version__)
    return parser


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return "%.0f%s" % (value, unit) if unit == "B" else "%.1f%s" % (value, unit)
        value /= 1024
    return "%.1fGB" % value


def list_sessions(out: IO[str], err: IO[str]) -> int:
    """Print the most recent sessions, newest first."""
    found = find_transcripts(limit=LIST_LIMIT)
    if not found:
        err.write("cc-replay: no transcripts found under %s\n" % projects_dir())
        return 2
    for item in found:
        when = datetime.fromtimestamp(item.mtime).strftime("%Y-%m-%d %H:%M")
        out.write("%s  %-8s  %-34s  %s\n" % (
            when, human_size(item.size), item.project[-34:], item.session_id))
    return 0


def resolve_input(args: argparse.Namespace, parser: argparse.ArgumentParser,
                  err: IO[str]) -> Optional[Path]:
    """Work out which transcript to read, reporting why if there is none."""
    if args.latest and args.path is None:
        newest = latest_transcript()
        if newest is None:
            err.write("cc-replay: no transcripts found under %s\n" % projects_dir())
            return None
        return newest
    if args.path is None:
        parser.error("a transcript path is required (or use --latest, or --list)")
    if not args.path.is_file():
        err.write("cc-replay: no such transcript: %s\n" % args.path)
        return None
    return args.path


def main(argv: Optional[List[str]] = None, out: Optional[IO[str]] = None,
         err: Optional[IO[str]] = None) -> int:
    out = sys.stdout if out is None else out
    err = sys.stderr if err is None else err
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        return list_sessions(out, err)

    source = resolve_input(args, parser, err)
    if source is None:
        return 2

    session = parse_transcript(source, max_events=args.max_events)
    if not args.no_redact:
        redact_session(session)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(session, redact=not args.no_redact), encoding="utf-8")

    counts = session.counts
    out.write("%s\n" % args.output.resolve())
    out.write("  %d steps (user %d, assistant %d, tool %d, unknown %d)%s\n" % (
        len(session.steps), counts.get("user", 0), counts.get("assistant", 0),
        counts.get("tool_calls", 0), counts.get("unknown", 0),
        "" if args.no_redact else ", redacted"))
    if session.malformed_lines or session.dropped_steps:
        out.write("  %d malformed lines, %d steps dropped\n" % (
            session.malformed_lines, session.dropped_steps))
    return 0
