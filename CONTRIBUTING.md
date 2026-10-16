# Contributing to cc-replay

Thanks for your interest! Bug reports and pull requests are welcome.

## Development setup

There is nothing to build and nothing to install at runtime.

```sh
python -m pip install pytest          # the only tool the suite needs
python -m pytest tests/ -q            # or: python -m unittest discover -s tests -v
python -m cc_replay --help
```

CI runs the suite on Python 3.9 and 3.12; please keep both working.

## Guidelines

- **Zero runtime dependencies.** Standard library only. Do not add a
  third-party import.
- **The page stays self-contained.** No CDN, web font, image or other network
  request from the generated HTML.
- **Escape before transforming.** Transcript text is HTML-escaped before any
  Markdown transform; keep it that way.
- **Redaction stays on by default.** Cover any new secret pattern with tests
  in `tests/test_redactor.py`, and read [SECURITY.md](SECURITY.md).
- **Synthetic fixtures only.** A test must never read a real transcript.
- `agent-standup` and `cc-stats` vendor `parser.py` and `redactor.py`, so a
  fix there is worth mentioning in the PR.
- Add a regression test for any bug fix.

## Pull requests

Keep PRs focused on one change, describe what changed and how you verified
it, and make sure the test suite is green before opening one.
