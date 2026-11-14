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
