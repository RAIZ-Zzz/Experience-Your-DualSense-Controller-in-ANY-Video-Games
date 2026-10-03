# Template: adding a game

1. Copy this folder to `games/<name>/` and rename `TemplateReader`.
2. Fill `config.toml` → `[game] process_names`, and `dsx_profile.toml` → `dsx_dir`, `name`.
3. Find the three hooks (`active`, `health`, `shot`) and the field offsets. The method is in
   `skill/dualsense-for-every-game/SKILL.md`; the tools are in `tools/re/`.
4. `scan.bat` must report exactly 1 match per signature, then `probe.bat` shows the objects and values.
5. `demo.bat` to tune the feel without the game, `start.bat` to play.
