import unittest

from neurhon.server.break_mode import (
    ACTIVE,
    EVENT_BREAK_ENDED,
    EVENT_OFFER,
    OFF,
    OFFER,
    WATCHING,
    BreakMonitor,
)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make(clock):
    monitor = BreakMonitor(
        threshold=0.3,
        low_seconds=20,
        break_seconds=600,
        cooldown_seconds=300,
        grace_seconds=120,
        clock=clock,
    )
    monitor.set_enabled(True)
    return monitor


def feed(monitor, clock, focus, seconds):
    """Podaje ten sam focus co sekundę przez `seconds` sekund, zwraca ostatnie zdarzenie."""
    event = None
    for _ in range(seconds):
        clock.advance(1)
        event = monitor.update(focus) or event
    return event


class BreakMonitorTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.monitor = make(self.clock)

    def test_starts_off_until_enabled(self):
        fresh = BreakMonitor(0.3, 20, 600, 300, 120, clock=self.clock)
        self.assertEqual(fresh.phase, OFF)
        self.assertIsNone(fresh.update(0.0))
        self.assertEqual(fresh.phase, OFF)

    def test_short_dip_does_not_trigger(self):
        feed(self.monitor, self.clock, 0.1, 10)
        feed(self.monitor, self.clock, 0.8, 1)  # focus wrócił
        feed(self.monitor, self.clock, 0.1, 15)
        self.assertEqual(self.monitor.phase, WATCHING)

    def test_long_low_focus_offers_break(self):
        event = feed(self.monitor, self.clock, 0.1, 25)
        self.assertEqual(event, EVENT_OFFER)
        self.assertEqual(self.monitor.phase, OFFER)

    def test_offer_waits_forever_for_decision(self):
        feed(self.monitor, self.clock, 0.1, 25)
        feed(self.monitor, self.clock, 0.9, 5000)
        self.assertEqual(self.monitor.phase, OFFER)

    def test_accept_starts_ten_minute_break(self):
        feed(self.monitor, self.clock, 0.1, 25)
        start = self.clock.now
        self.assertTrue(self.monitor.accept())
        self.assertEqual(self.monitor.phase, ACTIVE)
        self.assertEqual(self.monitor.ends_at, start + 600)

    def test_break_ends_by_itself(self):
        feed(self.monitor, self.clock, 0.1, 25)
        self.monitor.accept()
        self.assertIsNone(feed(self.monitor, self.clock, None, 599))
        self.assertEqual(self.monitor.phase, ACTIVE)
        self.assertEqual(feed(self.monitor, self.clock, None, 1), EVENT_BREAK_ENDED)
        self.assertEqual(self.monitor.phase, WATCHING)

    def test_grace_period_after_break(self):
        feed(self.monitor, self.clock, 0.1, 25)
        self.monitor.accept()
        self.assertTrue(self.monitor.end())
        feed(self.monitor, self.clock, 0.1, 100)  # w karencji (120 s): bez propozycji
        self.assertEqual(self.monitor.phase, WATCHING)
        feed(self.monitor, self.clock, 0.1, 60)  # karencja minęła, a focus nadal niski
        self.assertEqual(self.monitor.phase, OFFER)

    def test_dismiss_starts_cooldown(self):
        feed(self.monitor, self.clock, 0.1, 25)
        self.assertTrue(self.monitor.dismiss())
        self.assertEqual(self.monitor.phase, WATCHING)
        feed(self.monitor, self.clock, 0.1, 250)  # cooldown 300 s
        self.assertEqual(self.monitor.phase, WATCHING)
        feed(self.monitor, self.clock, 0.1, 100)
        self.assertEqual(self.monitor.phase, OFFER)

    def test_actions_in_wrong_phase_do_nothing(self):
        self.assertFalse(self.monitor.accept())
        self.assertFalse(self.monitor.dismiss())
        self.assertFalse(self.monitor.end())
        self.assertEqual(self.monitor.phase, WATCHING)

    def test_disable_resets_everything(self):
        feed(self.monitor, self.clock, 0.1, 25)
        self.monitor.accept()
        self.monitor.set_enabled(False)
        self.assertEqual(self.monitor.phase, OFF)
        self.assertIsNone(self.monitor.ends_at)

    def test_threshold_can_change(self):
        self.monitor.threshold = 0.6
        feed(self.monitor, self.clock, 0.5, 25)
        self.assertEqual(self.monitor.phase, OFFER)

    def test_snapshot_shape(self):
        self.assertEqual(
            self.monitor.snapshot(),
            {"enabled": True, "phase": WATCHING, "threshold": 0.3, "ends_at": None},
        )


if __name__ == "__main__":
    unittest.main()
