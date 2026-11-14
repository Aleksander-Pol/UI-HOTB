import importlib.util
import sys
import unittest
from types import SimpleNamespace

from neurhon.server.interfaces import Track
from neurhon.server.notify import NOT_NOW, STOP, DesktopNotifier, NullNotifier, create_notifier

HAS_LIB = importlib.util.find_spec("windows_toasts") is not None
TRACK = Track("Thunderstruck", "AC/DC", "Wake up")


class FakeToaster:
    def __init__(self):
        self.shown, self.removed = [], []

    def show_toast(self, toast):
        self.shown.append(toast)

    def remove_toast(self, toast):
        self.removed.append(toast)


class NullNotifierTest(unittest.TestCase):
    def test_does_nothing_and_does_not_fail(self):
        n = NullNotifier()
        n.show_offer(lambda: None, lambda: None, TRACK)
        n.close_offer()
        n.show_break_over()

    def test_factory_always_returns_something_usable(self):
        notifier = create_notifier()
        for method in ("show_offer", "close_offer", "show_break_over"):
            self.assertTrue(callable(getattr(notifier, method)))


@unittest.skipUnless(HAS_LIB and sys.platform == "win32", "needs windows-toasts on Windows")
class DesktopNotifierTest(unittest.TestCase):
    def setUp(self):
        self.toaster = FakeToaster()
        self.notifier = DesktopNotifier(toaster=self.toaster)
        self.calls = []
        self.notifier.show_offer(lambda: self.calls.append("stop"), lambda: self.calls.append("not_now"), TRACK)
        self.toast = self.toaster.shown[0]

    def test_toast_has_two_buttons_and_names_the_song(self):
        self.assertEqual(len(self.toast.actions), 2)
        self.assertIn("Thunderstruck", " ".join(self.toast.text_fields))

    def test_buttons_call_our_functions(self):
        self.toast.on_activated(SimpleNamespace(arguments=STOP))
        self.assertEqual(self.calls, ["stop"])

    def test_not_now_button(self):
        self.toast.on_activated(SimpleNamespace(arguments=NOT_NOW))
        self.assertEqual(self.calls, ["not_now"])

    def test_click_on_the_text_does_nothing(self):
        self.toast.on_activated(SimpleNamespace(arguments=""))
        self.assertEqual(self.calls, [])

    def test_close_offer_removes_the_toast_once(self):
        self.notifier.close_offer()
        self.notifier.close_offer()
        self.assertEqual(self.toaster.removed, [self.toast])

    def test_break_over_toast(self):
        self.notifier.show_break_over()
        self.assertEqual(len(self.toaster.shown), 2)


if __name__ == "__main__":
    unittest.main()
