"""ANTI_CHEAT_RULES.md, enforced: every game documents switching the anti-cheat off and restoring it,
and the memory layer keeps refusing while an anti-cheat runs."""
import unittest
from pathlib import Path

from dualsense.memory import ANTI_CHEAT_PROCESSES, anti_cheat_running

GAMES = Path(__file__).resolve().parent.parent / "games"
REQUIRED = ("## Anti-cheat off (offline only)", "## Restore the anti-cheat")


class Rules(unittest.TestCase):
    def test_every_game_documents_anti_cheat_off_and_restore(self):
        for game in GAMES.iterdir():
            if game.is_dir() and not game.name.startswith(("_", ".")) and game.name != "__pycache__":
                readme = (game / "README.md").read_text(encoding="utf-8") if (game / "README.md").exists() else ""
                for heading in REQUIRED:
                    self.assertIn(heading, readme, f"games/{game.name}/README.md needs '{heading}'")

    def test_memory_layer_refuses_while_anti_cheat_runs(self):
        self.assertIn("easyanticheat.exe", ANTI_CHEAT_PROCESSES)
        self.assertTrue(anti_cheat_running([(1, "easyanticheat.exe")]))


if __name__ == "__main__":
    unittest.main()
