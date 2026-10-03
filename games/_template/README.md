# Template: adding a game

1. Copy this folder to `games/<game_name>/` (full game name, e.g. `star_wars_squadrons`) on the right
   branch: `single-player` if the game has no anti-cheat, `online` if it has one. Rename `TemplateReader`.
2. Keep `MODLOG.md` as you go. Fill `config.toml` → `[game] process_names`, and `dsx_profile.toml` →
   `dsx_dir`, `name`.
3. Find the three hooks (`active`, `health`, `shot`) and the field offsets. Method: the skill
   (`skill/dualsense-for-every-game/SKILL.md`); tools: `tools/re/`. Put the exact runs you used in
   `research/*.bat`, so they can be re-run.
4. `scan.bat` must report exactly 1 match per signature, then `probe.bat` shows the objects and values.
5. `demo.bat` to tune the feel without the game, `start.bat` to play.
6. Replace this README with the game's: sections below.

---

# <Game name>

<Store> build **<version>**, PC. Offline modes: <...>.

## Evidence

| File | Size | Date | SHA-256 |
|---|---|---|---|
| <!-- python tools/evidence.py <exe> --> | | | |

Static inference vs runtime evidence: say which of the findings below were seen in the running game
(call counts, values) and which are only read from code.

## Anti-cheat off (offline only)

<!-- online branch only: documented, reversible method; which modes still work -->

## Restore the anti-cheat

<!-- online branch only: e.g. the store's Repair -->

## How the hooks were found

## Measured

## Files
