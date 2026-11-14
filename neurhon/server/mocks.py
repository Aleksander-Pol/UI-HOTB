"""Fake implementations of the interfaces, used until the real ones exist.

They let the UI run and be tested without the EEG headband or Spotify.
"""

import random
import time

from neurhon.server.interfaces import Mood, MoodProvider, MusicController, Track

# Typowe wartości (energy, valence, focus) dla każdej etykiety nastroju.
# "tired" ma niski focus, więc w demo to ten nastrój uruchamia propozycję przerwy.
_MOOD_CENTERS = {
    "calm": (0.2, 0.7, 0.5),
    "focused": (0.6, 0.6, 0.85),
    "stressed": (0.85, 0.2, 0.45),
    "tired": (0.15, 0.3, 0.2),
}


def _jitter(value: float, amount: float = 0.08) -> float:
    """Nudge a value a little and keep it inside 0..1."""
    return min(1.0, max(0.0, value + random.uniform(-amount, amount)))


class MockMoodProvider(MoodProvider):
    """Returns a made-up mood that changes label every few seconds."""

    def __init__(self, change_every: float = 8.0):
        self._change_every = change_every
        self._label = random.choice(list(_MOOD_CENTERS))
        self._changed_at = time.time()

    def get_mood(self) -> Mood:
        now = time.time()
        if now - self._changed_at >= self._change_every:
            self._label = random.choice(list(_MOOD_CENTERS))
            self._changed_at = now

        energy, valence, focus = _MOOD_CENTERS[self._label]
        return Mood(
            label=self._label,
            scores={
                "valence": _jitter(valence),
                "energy": _jitter(energy),
                "focus": _jitter(focus),
            },
            timestamp=now,
        )


# Made-up songs, just enough for the UI to have something to show.
_MOCK_TRACKS = [
    Track("Weightless", "Marconi Union", "Calm Focus"),
    Track("Strobe", "deadmau5", "Deep Work"),
    Track("Clair de Lune", "Claude Debussy", "Evening Wind Down"),
    Track("Time", "Hans Zimmer", "Deep Work"),
]


class MockMusicController(MusicController):
    """A pretend player: it only changes state in memory, no sound is played."""

    def __init__(self):
        self._index = 0
        self._playing = False
        self._override = None  # utwór puszczony przez play_track (np. na przerwę)

    def play(self) -> None:
        self._playing = True

    def pause(self) -> None:
        self._playing = False

    def next_track(self) -> None:
        self._override = None
        self._index = (self._index + 1) % len(_MOCK_TRACKS)

    def play_track(self, track: Track) -> None:
        self._override = track
        self._playing = True

    def now_playing(self) -> Track | None:
        return self._override or _MOCK_TRACKS[self._index]

    def is_playing(self) -> bool:
        return self._playing
