# Experience Your DualSense Controller in ANY Video Game: single-player games

**Branch `single-player`**: single-player games **without** an anti-cheat. Game state is read from, and
lightly hooked into, the running game's memory. Offline use only.

Games with online modes and an anti-cheat (EAC, BattlEye, ...) are on the [`online`](../../tree/online)
branch, under stricter rules; [`main`](../../tree/main) explains both branches.

## Games

None yet. Star Wars: Squadrons has EAC, so it lives on the `online` branch.

## Adding a game

1. Check that the game really has no anti-cheat. If it has one, the game belongs on `online`.
2. Copy `games/_template` to `games/<name>/`, set the exe name in `config.toml` and `dsx_dir` / `name` in
   `dsx_profile.toml`.
3. Find three hooks: code that runs every frame while playing, code that reads the player's health, and
   code that runs exactly once per shot. Method and tools:
   [`skill/dualsense-for-every-game/SKILL.md`](skill/dualsense-for-every-game/SKILL.md), `tools/re/`.
4. `scan.bat` → exactly 1 match per signature, `probe.bat` → objects and values, `demo.bat` → tune the
   feel, `start.bat` → play.

Requirements: Windows 10/11, Python 3.11+ (stdlib only for playing), DSX v3 with
*Settings → Networking → Incoming UDP* on and virtual device **Xbox 360**.

## Prior art and credits

The workflow borrows from other projects (universal-modder, the awesome-game-security reverse-engineering
skill, and existing DSX mods such as ForzaDSX, RDR2 – DSX and Cyberpunk's DualSense mods). Each idea, with
what was taken and what was not:
[`skill/dualsense-for-every-game/references/prior-art.md`](skill/dualsense-for-every-game/references/prior-art.md).

## License

MIT
