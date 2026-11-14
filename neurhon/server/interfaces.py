"""Contracts shared between the EEG side, the music side and the UI.

Everything in the system talks in terms of these types, so teammates can
work in parallel as long as they respect them.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass  #omijamy pisanie initów itd. robi to za nas
class Mood:

    label: str  # nazwa stanu emocjonalnego
    scores: dict[str, float] = field(default_factory=dict) #metryki stan, odczyt stanu
    timestamp: float = 0.0 # czas odczytu stanu


class MoodProvider(ABC): #abstrakcyjna
    """ Interfejs który ma dostarczać aktualny stan emocjonalny"""

    @abstractmethod
    def get_mood(self) -> Mood:
        """Zwraca odczyt stanu"""


@dataclass
class Track:
    """Obecny utwór ma tytuł wykonawe i playlistę"""

    title: str
    artist: str
    playlist: str = ""


class MusicController(ABC):
    """ Interfejs do sterowania odtwarzaczem muzyki. Ma wszystkie metody które są potrzebne do sterowania"""

    @abstractmethod
    def play(self) -> None:
        """Odtwarzaj muze."""

    @abstractmethod
    def pause(self) -> None:
        """Zapauzuj muze"""

    @abstractmethod
    def next_track(self) -> None:
        """Nastepny utwór"""

    @abstractmethod
    def play_track(self, track: Track) -> None:
        """Zagraj dokładnie ten utwór (np. utwór na przerwę)."""

    @abstractmethod
    def now_playing(self) -> Track | None:
        """Co teraz jest grane"""

    @abstractmethod
    def is_playing(self) -> bool:
        """Czy wgl jest coś grane"""


@dataclass
class HistoryEntry:
    """To jest rekord w historii odtwarzania. Reason wskazuje dlaczego doszło do zmiany"""

    timestamp: float
    track: Track
    mood: Mood
    reason: str = "auto"


class HistoryStore(ABC):
    """Definiuje format zapisu do bazy danych (bądź do json file)"""

    @abstractmethod
    def append(self, entry: HistoryEntry) -> None:
        """Save one entry at the end of the history."""

    @abstractmethod
    def get_entries(self, limit: int = 100, since: float | None = None) -> list[HistoryEntry]:
        """Get the last `limit` entries, optionally only those after `since` timestamp."""

