"""HookReader behaviour without a game: unfilled template, game starting / closing."""
import unittest

from dualsense import reader
from dualsense.effects import GameState
from dualsense.hook import GameNotReady, InstalledSpy, Spy
from games._template.reader import TemplateReader


class Filled(TemplateReader):
    """The template with its signatures filled in (so attaching gets as far as reading memory)."""
    SPIES = {name: Spy(name, "90 90 90 90 90 90", 0, 5, "rbx") for name in ("active", "health", "shot")}


class Template(unittest.TestCase):
    def test_unfilled_template_waits_instead_of_crashing(self):
        from games._template.reader import TemplateReader
        r = TemplateReader(["x.exe"], clock=lambda: 0.0, trigger=lambda: 0)
        self.assertEqual(r.read(), GameState())
        self.assertIn("not filled in", r.last_error)


class GameClosing(unittest.TestCase):
    class ClosingGame:
        """A game process whose memory is already gone: code found by the scan, but every read fails."""
        base, size = 0x140000000, 0x1000
        def scan(self, pattern, start=None, size=None): return [0x140000100]
        def read(self, addr, n): return None
        def alive(self): return True
        def close(self): pass

    def test_install_reports_not_ready(self):
        with self.assertRaises(GameNotReady):
            InstalledSpy.install(self.ClosingGame(), Spy("t", "90 90 90 90 90 90", 0, 5, "rbx"))

    def test_reader_waits_instead_of_crashing(self):
        orig = reader.Process.find
        reader.Process.find = staticmethod(lambda names, write=False: GameClosing.ClosingGame())
        try:
            r = Filled(["x.exe"], clock=lambda: 0.0, trigger=lambda: 0)
            self.assertEqual(r.read(), GameState())          # the crash you hit: now just "not ready"
            self.assertIsNone(r.proc)
            self.assertGreater(r.retry_at, 0.0)               # and it waits before scanning again
        finally:
            reader.Process.find = orig



if __name__ == "__main__":
    unittest.main()
