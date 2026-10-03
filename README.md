# Experience Your DualSense Controller in ANY Video Game

Give PC games that never supported the PS5 controller **adaptive triggers and a live lightbar**, driven by
what actually happens in the game: one trigger kick per shot fired, a lightbar that follows your health.

It works by reading (and lightly hooking) the running game's memory and sending effects to
[DSX](https://store.steampowered.com/app/1812620/DSX/), which owns the controller.

| Game | Triggers | Lightbar | Notes |
|---|---|---|---|
| Star Wars: Squadrons (EA app 1.0.10.39591) | ✅ one pulse per shot, any ship | ✅ hull: green → red | [games/squadrons](games/squadrons/README.md) |

Body haptics are still being explored (see *Haptics* below).

> **Offline / single-player only.** This patches a few instructions in the running game. Never use it with
> online play or with an anti-cheat running: the memory layer refuses to attach while EasyAntiCheat is up,
> and you should keep it that way.

## Requirements

- Windows 10/11, Python 3.11+ (stdlib only for playing)
- DSX v3 (Steam). In DSX: *Settings → Networking → Incoming UDP* on, virtual device **Xbox 360**.
- A game build whose code signatures are in `games/<name>/reader.py`

## Play (Squadrons)

1. Set `dsx_dir` in `games/squadrons/dsx_profile.toml` to your DSX folder.
2. Close DSX, run `games/squadrons/apply-dsx-profile.bat`, start DSX.
3. Run `games/squadrons/start.bat` (it waits for the game), then launch the game.
4. `demo.bat` lets you feel and tune the effects without the game; tuning lives in `config.toml`.

## Layout

```
dualsense/            game-agnostic core
  dsx.py              DSX UDP protocol (trigger modes, RGB)
  memory.py           process memory: attach, read, AOB scan, write / allocate
  hook.py             register spy: patch an instruction to record the object it works on
  reader.py           HookReader: game state from a few hooks (a game only declares which hook is which)
  player.py           PlayerPicker: the player's object = the one whose code runs while you press RT
  effects.py          GameState -> RT effect (pulse per shot) and lightbar colour
  bridge.py           loop, demo, probe, CLI
  profile.py          DSX profile generator from dsx_profile.toml
games/<name>/         one folder per game: reader.py, config.toml, dsx_profile.toml, *.bat
games/_template/      start here for a new game
tools/re/             reverse-engineering helpers (find writers, count calls, find callers, audio pan)
tools/haptics/        tests for the haptics output paths
skill/                Claude Code skill describing the whole workflow
tests/                python -m unittest discover tests
```

## Adding a game

Copy `games/_template`, then find three hooks: code that runs every frame while playing, code that
reads the player's health, and code that runs exactly once per shot. The method (and what went wrong
along the way) is in [`skill/dualsense-for-every-game/SKILL.md`](skill/dualsense-for-every-game/SKILL.md).
With [Claude Code](https://claude.com/claude-code), copy that folder to `~/.claude/skills/` and run
`/dualsense-for-every-game`.

## Haptics (work in progress)

Through Xbox emulation, game rumble reaches the DualSense as "left = heavy, right = light", so a balanced
left/right effect is not possible on that path (tested down to left 8 % vs right 100 %: left still
stronger). DSX's UDP interface exposes triggers and LEDs, not the haptic actuators. Audio-to-haptics
(DSX+ over Bluetooth) is stereo but listens to the system output. `tools/haptics/` has the tests.

## License

MIT
