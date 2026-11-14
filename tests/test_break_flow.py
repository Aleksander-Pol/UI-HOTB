import unittest

from neurhon.server.break_flow import BreakFlow
from neurhon.server.break_mode import ACTIVE, OFF, OFFER, WATCHING, BreakMonitor
from neurhon.server.interfaces import Track
from neurhon.server.mocks import MockMusicController

WAKE = [Track("Never Gonna Give You Up", "Rick Astley", "Wake up"), Track("Thunderstruck", "AC/DC", "Wake up")]


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SpyNotifier:
    def __init__(self):
        self.offers = []  # (on_stop, on_not_now, track)
        self.closed = 0
        self.break_over = 0

    def show_offer(self, on_stop, on_not_now, track):
        self.offers.append((on_stop, on_not_now, track))

    def close_offer(self):
        self.closed += 1

    def show_break_over(self):
        self.break_over += 1


class BrokenNotifier(SpyNotifier):
    def show_offer(self, *args):
        raise RuntimeError("no toast today")


class BrokenMusic(MockMusicController):
    def play_track(self, *args, **kwargs):
        raise RuntimeError("no active device")


def build(music=None, notifier=None):
    clock = FakeClock()
    monitor = BreakMonitor(
        threshold=0.3, low_seconds=20, break_seconds=600, cooldown_seconds=600, grace_seconds=0, clock=clock
    )
    music = music or MockMusicController()
    notifier = notifier or SpyNotifier()
    history = []
    flow = BreakFlow(
        monitor, music, notifier, WAKE, 80,
        on_wake_started=lambda focus: history.append(focus),
        choose=lambda tracks: tracks[0],
    )
    flow.set_enabled(True)
    return flow, music, notifier, clock, history


def feed(flow, clock, focus, seconds):
    for _ in range(seconds):
        clock.advance(1)
        flow.tick(focus)


class BreakFlowTest(unittest.TestCase):
    def test_low_focus_starts_loud_looping_music_and_push(self):
        flow, music, notifier, clock, history = build()
        music.play()  # użytkownik słuchał własnej muzyki
        feed(flow, clock, 0.1, 25)

        self.assertEqual(flow.phase, OFFER)
        self.assertEqual(music.now_playing().title, "Never Gonna Give You Up")
        self.assertEqual(music.volume, 80)
        self.assertTrue(music.repeating)
        self.assertEqual(len(notifier.offers), 1)
        self.assertEqual(notifier.offers[0][2], WAKE[0])
        self.assertEqual(len(history), 1)  # wpis w historii o starcie muzyki

    def test_not_now_restores_previous_music_and_gives_ten_quiet_minutes(self):
        flow, music, notifier, clock, _ = build()
        music.play()
        before = music.now_playing().title
        feed(flow, clock, 0.1, 25)

        self.assertTrue(flow.dismiss())
        self.assertEqual(flow.phase, WATCHING)
        self.assertEqual(notifier.closed, 1)
        self.assertEqual(music.now_playing().title, before)
        self.assertTrue(music.is_playing())  # dawna muzyka gra dalej
        self.assertEqual(music.volume, 50)
        self.assertFalse(music.repeating)

        feed(flow, clock, 0.1, 590)  # focus ignorowany przez 10 minut
        self.assertEqual(flow.phase, WATCHING)
        feed(flow, clock, 0.1, 40)
        self.assertEqual(flow.phase, OFFER)

    def test_stop_music_starts_silent_break_and_old_music_returns_at_the_end(self):
        flow, music, notifier, clock, _ = build()
        music.play()
        before = music.now_playing().title
        feed(flow, clock, 0.1, 25)

        self.assertTrue(flow.accept())
        self.assertEqual(flow.phase, ACTIVE)
        self.assertTrue(flow.suspended)
        self.assertFalse(music.is_playing())  # cisza w czasie przerwy
        self.assertEqual(music.volume, 50)  # głośność wraca od razu
        self.assertEqual(notifier.closed, 1)

        for _ in range(599):  # przerwa trwa, focus nie jest czytany
            clock.advance(1)
            flow.tick(None)
        self.assertTrue(flow.suspended)
        self.assertFalse(music.is_playing())

        clock.advance(1)
        flow.tick(None)  # minęło 10 minut
        self.assertEqual(flow.phase, WATCHING)
        self.assertTrue(music.is_playing())  # dawna muzyka wraca
        self.assertEqual(music.now_playing().title, before)
        self.assertEqual(notifier.break_over, 1)

    def test_focus_is_measured_right_after_break_ends(self):
        flow, music, notifier, clock, _ = build()
        feed(flow, clock, 0.1, 25)
        flow.accept()
        clock.advance(601)
        flow.tick(None)

        feed(flow, clock, 0.1, 19)
        self.assertEqual(flow.phase, WATCHING)  # warunek 20 s nadal obowiązuje
        feed(flow, clock, 0.1, 2)
        self.assertEqual(flow.phase, OFFER)  # i muzyka wraca, jeśli focus nadal niski

    def test_ending_break_early_resumes_music_without_break_over_push(self):
        flow, music, notifier, clock, _ = build()
        music.play()
        feed(flow, clock, 0.1, 25)
        flow.accept()

        self.assertTrue(flow.end())
        self.assertEqual(flow.phase, WATCHING)
        self.assertTrue(music.is_playing())
        self.assertEqual(notifier.break_over, 0)
        feed(flow, clock, 0.1, 21)  # na własne ryzyko: focus od razu mierzony
        self.assertEqual(flow.phase, OFFER)

    def test_nothing_playing_before_means_silence_after_not_now(self):
        flow, music, _, clock, _ = build()  # nic nie grało
        feed(flow, clock, 0.1, 25)
        self.assertTrue(music.is_playing())  # muzyka pobudzająca gra
        flow.dismiss()
        self.assertFalse(music.is_playing())

    def test_disabling_during_wake_restores_music_and_closes_push(self):
        flow, music, notifier, clock, _ = build()
        music.play()
        feed(flow, clock, 0.1, 25)
        flow.set_enabled(False)
        self.assertEqual(flow.phase, OFF)
        self.assertEqual(notifier.closed, 1)
        self.assertTrue(music.is_playing())
        self.assertEqual(music.volume, 50)

    def test_disabling_during_break_returns_old_music(self):
        flow, music, _, clock, _ = build()
        music.play()
        feed(flow, clock, 0.1, 25)
        flow.accept()
        flow.set_enabled(False)
        self.assertEqual(flow.phase, OFF)
        self.assertTrue(music.is_playing())

    def test_music_failure_does_not_block_the_offer(self):
        flow, music, notifier, clock, history = build(music=BrokenMusic())
        feed(flow, clock, 0.1, 25)
        self.assertEqual(flow.phase, OFFER)
        self.assertEqual(len(notifier.offers), 1)  # push i baner i tak się pokazują
        self.assertTrue(flow.accept())  # i przerwę da się zacząć

    def test_notification_failure_does_not_block_the_flow(self):
        flow, music, notifier, clock, _ = build(notifier=BrokenNotifier())
        feed(flow, clock, 0.1, 25)
        self.assertEqual(flow.phase, OFFER)
        self.assertTrue(music.is_playing())
        self.assertTrue(flow.dismiss())

    def test_push_buttons_call_the_same_actions(self):
        flow, music, notifier, clock, _ = build()
        feed(flow, clock, 0.1, 25)
        on_stop, on_not_now, _ = notifier.offers[0]
        on_stop()
        self.assertEqual(flow.phase, ACTIVE)

    def test_test_button_runs_the_whole_sequence_and_enables_break_mode(self):
        flow, music, notifier, clock, history = build()
        flow.set_enabled(False)
        self.assertEqual(flow.phase, OFF)

        self.assertTrue(flow.test())
        self.assertEqual(flow.phase, OFFER)
        self.assertEqual(len(notifier.offers), 1)
        self.assertEqual(music.volume, 80)
        self.assertEqual(history, [None])  # bez realnego focusu
        self.assertFalse(flow.test())  # w trakcie budzenia kolejny test nic nie robi

    def test_unneeded_actions_do_nothing(self):
        flow, *_ = build()
        self.assertFalse(flow.accept())
        self.assertFalse(flow.dismiss())
        self.assertFalse(flow.end())


if __name__ == "__main__":
    unittest.main()
