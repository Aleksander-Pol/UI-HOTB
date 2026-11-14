"""Settings that the server and the UI share: moods, metrics, paths, secrets.

Teammates add a new mood label or metric here, and the UI picks it up.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Metric:
    """A named score that can appear in Mood.scores (value range 0..1)."""

    id: str
    title: str
    description: str


@dataclass(frozen=True)
class MoodLabel:
    """A mood name, its accent color, and where it sits on the arousal/valence map."""

    id: str
    title: str
    color: str
    arousal: float
    valence: float


METRICS = [
    Metric("arousal", "Arousal", "How activated you are, from sleepy to energized."),
    Metric("valence", "Valence", "How pleasant the state is, from unpleasant to pleasant."),
]

MOOD_LABELS = [
    MoodLabel("calm", "Calm", "#4f8cff", arousal=0.2, valence=0.7),
    MoodLabel("focused", "Focused", "#2fbf9b", arousal=0.6, valence=0.6),
    MoodLabel("stressed", "Stressed", "#ef5b5b", arousal=0.85, valence=0.2),
    MoodLabel("tired", "Tired", "#a58bd9", arousal=0.15, valence=0.3),
]

DATA_DIR = Path("data")
HISTORY_PATH = DATA_DIR / "history.jsonl"


@lru_cache(maxsize=1)
def load_env(path: str = ".env") -> dict[str, str]:
    """Read KEY=VALUE lines from a .env file. A missing file gives an empty dict."""
    env_file = Path(path)
    if not env_file.exists():
        return {}

    values = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_setting(name: str, default: str | None = None) -> str | None:
    """Look a setting up in the environment first, then in the .env file."""
    return os.environ.get(name) or load_env().get(name) or default
