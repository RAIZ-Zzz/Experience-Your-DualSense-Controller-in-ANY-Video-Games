"""Star Wars: Squadrons: hook declarations and config (no game needed)."""
import tomllib
import unittest
from pathlib import Path

from games.squadrons.reader import SPIES


class Signatures(unittest.TestCase):
    def test_hooks_fit_their_signatures(self):
        for spy in SPIES.values():
            self.assertGreaterEqual(spy.stolen, 5)
            self.assertLessEqual(spy.offset + spy.stolen, len(spy.pattern.split()))

    def test_config_has_every_section(self):
        cfg = tomllib.loads((Path(__file__).parent.parent / "games/squadrons/config.toml").read_text(encoding="utf-8"))
        for section in ("dsx", "loop", "game", "fire", "hit", "lightbar"):
            self.assertIn(section, cfg)



if __name__ == "__main__":
    unittest.main()
