"""Find Claude Code transcripts on disk, newest first."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ENV_CONFIG_DIR = "CLAUDE_CONFIG_DIR"


@dataclass
class TranscriptFile:
    path: Path
    project: str
    session_id: str
    size: int
    mtime: float


def config_dir() -> Path:
    """Claude Code's config directory, honouring ``CLAUDE_CONFIG_DIR``."""
    override = os.environ.get(ENV_CONFIG_DIR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude"


def projects_dir() -> Path:
    return config_dir() / "projects"


def find_transcripts(limit: Optional[int] = None) -> List[TranscriptFile]:
    """All ``*.jsonl`` transcripts across project directories, newest first."""
    root = projects_dir()
    found = []  # type: List[TranscriptFile]
    if not root.is_dir():
        return found
    for path in root.glob("*/*.jsonl"):
        try:
            stat = path.stat()
        except OSError:
            continue
        found.append(TranscriptFile(path=path, project=path.parent.name,
                                    session_id=path.stem, size=stat.st_size,
                                    mtime=stat.st_mtime))
    found.sort(key=lambda item: item.mtime, reverse=True)
    return found[:limit] if limit else found


def latest_transcript() -> Optional[Path]:
    """The most recently modified transcript, or ``None`` if there are none."""
    newest = find_transcripts(limit=1)
    return newest[0].path if newest else None
