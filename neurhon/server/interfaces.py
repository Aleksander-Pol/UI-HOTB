"""Contracts shared between the EEG side, the music side and the UI.

Everything in the system talks in terms of these types, so teammates can
work in parallel as long as they respect them.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Mood:
    """One mood reading at a single moment in time.

    label:     human readable name of the state, e.g. "focused" or "calm".
    scores:    named metrics, each in the range 0..1,
               e.g. {"arousal": 0.7, "valence": 0.4, "focus": 0.8}.
               New metrics are just new keys, no change to this class needed.
    timestamp: unix time (seconds) of the reading.
    """

    label: str
    scores: dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0


class MoodProvider(ABC):
    """Source of mood readings.

    The EEG side implements this. The server only ever calls get_mood(),
    so it does not need to know whether the data comes from a headband
    or from a mock.
    """

    @abstractmethod
    def get_mood(self) -> Mood:
        """Return the most recent mood reading."""


@dataclass
class Track:
    """A song that is currently playing (or was last played)."""

    title: str
    artist: str
    playlist: str = ""


class MusicController(ABC):
    """Remote control for the music player.

    The Spotify side implements this. The UI buttons (play, pause, next)
    and the auto mode both go through these methods.
    """

    @abstractmethod
    def play(self) -> None:
        """Start or resume playback."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""

    @abstractmethod
    def next_track(self) -> None:
        """Skip to the next song."""

    @abstractmethod
    def now_playing(self) -> Track | None:
        """Return the current song, or None if nothing is loaded."""

    @abstractmethod
    def is_playing(self) -> bool:
        """Return True while music is playing, False when paused."""


@dataclass
class HistoryEntry:
    """One record in the listening history: a song change and why it happened."""

    timestamp: float
    track: Track
    mood: Mood
    reason: str = "auto"


class HistoryStore(ABC):
    """Storage for the listening history.

    The first implementation writes a JSON Lines file. Because the server
    only uses these two methods, it can be swapped for SQLite later without
    touching the server or the UI.
    """

    @abstractmethod
    def append(self, entry: HistoryEntry) -> None:
        """Save one entry at the end of the history."""

    @abstractmethod
    def get_entries(self, limit: int = 100, since: float | None = None) -> list[HistoryEntry]:
        """Return up to `limit` newest entries, newest first.

        If `since` is given (unix time), skip entries older than that.
        """

