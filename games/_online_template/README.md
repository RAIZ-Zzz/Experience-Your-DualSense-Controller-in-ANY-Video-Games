# Template: adding an online game

1. Read `ONLINE_RULES.md`. Find a source the game allows: official UDP telemetry, a game-state API,
   your own input, or your audio output.
2. Copy this folder to `games/<name>/`, rename the class, set `[telemetry] port` in `config.toml`
   and `dsx_dir` / `name` in `dsx_profile.toml`.
3. Implement `parse()` from the game's published packet format (shots as a delta of a counter if the
   game sends a total).
4. `demo.bat` to tune the feel, `start.bat` to play. `python -m unittest discover tests` must pass,
   including the online guard (tests/test_online.py).
