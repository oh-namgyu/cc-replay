# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-10-16

### Fixed

- Redaction: the generic credential rule no longer treats a backslash as part
  of a secret value. In serialized JSON it could swallow the backslash of an
  escaped quote and corrupt the session data embedded in the page.

## [0.1.0] - 2026-09-02

Initial public release.

### Added

- `python -m cc_replay` converts one Claude Code `.jsonl` transcript into a
  single self-contained HTML timeline. `--latest` picks the most recently
  modified session, `--list` prints the 20 most recent, `-o` sets the output
  path (default `replay.html`). Transcripts are read from
  `~/.claude/projects/`, or from `CLAUDE_CONFIG_DIR` when set.
- Timeline of user, assistant, thinking, system and tool steps with UTC
  timestamps; tool calls paired with their results by id, collapsed by
  default, with errors highlighted and missing results marked.
- Subagent (sidechain) steps nested under the tool call that spawned them.
- Playback bar: step back, play/pause, step forward, scrubber and step
  counter, with keyboard shortcuts.
- Minimal Markdown rendering on top of HTML-escaped text; links only for
  `http`/`https`, images never load.
- Dark and light themes via `prefers-color-scheme`.
- The page inlines its CSS, JavaScript, data and favicon and makes no network
  requests.
- Redaction on by default, in two passes (parsed tree, then serialized JSON):
  common API key and token formats, `Bearer` tokens, generic credential
  assignments, JWTs, private key blocks, email addresses and home paths.
  `--no-redact` writes the session verbatim and marks the page as unredacted.
- Limits for large sessions: `--max-events` (default 5000) keeps the last N
  steps, and oversized blocks are truncated at 50,000 characters or 1,000
  lines with a visible marker.
- Forgiving parser: unknown event types are kept as raw JSON blocks, invalid
  lines are skipped and counted, and a truncated final line is tolerated.
- Standard library only, Python 3.9+.
