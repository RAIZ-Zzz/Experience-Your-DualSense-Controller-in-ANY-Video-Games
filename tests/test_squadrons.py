"""Star Wars: Squadrons reader tests (no game needed)."""
import tomllib
import unittest
from pathlib import Path

from dualsense.effects import GameState
from dualsense.hook import GameNotReady, InstalledSpy, Spy
from dualsense import reader
from games.squadrons.reader import SPIES, SquadronsReader


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
            r = SquadronsReader(["x.exe"], clock=lambda: 0.0, trigger=lambda: 0)
            self.assertEqual(r.read(), GameState())          # the crash you hit: now just "not ready"
            self.assertIsNone(r.proc)
            self.assertGreater(r.retry_at, 0.0)               # and it waits before scanning again
        finally:
            reader.Process.find = orig



class Signatures(unittest.TestCase):
    def test_hooks_fit_their_signatures(self):
        for spy in SPIES.values():
            self.assertGreaterEqual(spy.stolen, 5)
            self.assertLessEqual(spy.offset + spy.stolen, len(spy.pattern.split()))

    def test_config_has_every_section(self):
        cfg = tomllib.loads((Path(__file__).parent.parent / "games/squadrons/config.toml").read_text(encoding="utf-8"))
        for section in ("dsx", "loop", "game", "fire", "hit", "lightbar"):
            self.assertIn(section, cfg)


class Template(unittest.TestCase):
    def test_unfilled_template_waits_instead_of_crashing(self):
        from games._template.reader import TemplateReader
        r = TemplateReader(["x.exe"], clock=lambda: 0.0, trigger=lambda: 0)
        self.assertEqual(r.read(), GameState())
        self.assertIn("not filled in", r.last_error)


if __name__ == "__main__":
    unittest.main()
