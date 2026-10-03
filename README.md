# Experience Your DualSense Controller in ANY Video Game: games with anti-cheat

**Branch `online`**: games that have online modes and an anti-cheat (EasyAntiCheat, BattlEye, ...).
They are supported **only in their offline modes, with the anti-cheat switched off**, and the anti-cheat
is restored before any online play. Read [ANTI_CHEAT_RULES.md](ANTI_CHEAT_RULES.md) first.

Single-player games without anti-cheat are on [`single-player`](../../tree/single-player);
[`main`](../../tree/main) explains both branches.

| Game | Offline modes | Triggers | Lightbar | Notes |
|---|---|---|---|---|
| Star Wars: Squadrons (EA app 1.0.10.39591) | Story, Practice | ✅ one pulse per shot, any ship | ✅ hull: green → red | [games/star_wars_squadrons](games/star_wars_squadrons/README.md) |

<img src="docs/images/star-wars-squadrons-lightbar.png" width="420" alt="DualSense lightbar turning yellow as the TIE fighter's hull drops">

*The lightbar follows the hull: yellow here after taking damage in a TIE fighter.*

Scripts for this game: [`games/star_wars_squadrons/`](games/star_wars_squadrons/) (play, demo, probe, profile)
and [`games/star_wars_squadrons/research/`](games/star_wars_squadrons/research/) (how its hooks were found).

## Play (Squadrons)

1. Switch EAC off for offline play: [games/star_wars_squadrons/README.md](games/star_wars_squadrons/README.md#anti-cheat-off-offline-only).
2. Set `dsx_dir` in `games/star_wars_squadrons/dsx_profile.toml` to your DSX folder.
3. Close DSX, run `games/star_wars_squadrons/apply-dsx-profile.bat`, start DSX.
4. Run `games/star_wars_squadrons/start.bat` (it waits for the game), then launch the game. Story or Practice only.
5. Before playing online: close `start.bat`, then *Repair* the game in the EA app to restore EAC.

`demo.bat` lets you feel and tune the effects without the game; tuning lives in `config.toml`.

## Adding a game

Copy `games/_template` to `games/<name>/`, then find three hooks: code that runs every frame while
playing, code that reads the player's health, and code that runs exactly once per shot. The game's
README must document how the anti-cheat is switched off for offline play and how it is restored
(`tests/test_rules.py` checks it). The method is in
[`skill/dualsense-for-every-game/SKILL.md`](skill/dualsense-for-every-game/SKILL.md).

## Haptics (work in progress)

Through Xbox emulation, game rumble reaches the DualSense as "left = heavy, right = light", so a balanced
left/right effect is not possible on that path (tested down to left 8 % vs right 100 %: left still
stronger). DSX's UDP interface exposes triggers and LEDs, not the haptic actuators. Audio-to-haptics
(DSX+ over Bluetooth) is stereo but listens to the system output. `tools/haptics/` has the tests.

## License

MIT
