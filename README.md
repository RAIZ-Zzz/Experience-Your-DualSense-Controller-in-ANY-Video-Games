# Experience Your DualSense Controller in ANY Video Game

Give PC games that never supported the PS5 controller **adaptive triggers and a live lightbar**, driven by
what actually happens in the game: one trigger kick per shot fired, a lightbar that follows your health.
Effects are sent to [DSX](https://store.steampowered.com/app/1812620/DSX/), which owns the controller.

## Two tracks, two branches

How a game's state may be read depends on whether the game is played online:

| | [`single-player`](../../tree/single-player) | [`online`](../../tree/online) |
|---|---|---|
| For | offline / single-player games, played with anti-cheat off | games played online, with their anti-cheat running |
| Data source | anything: reads and hooks the game's memory | only sources the game allows: official telemetry / game-state APIs, your own controller input, the PC's audio output |
| Game memory | read + patched (offline only; refuses to attach while EasyAntiCheat runs) | **never opened**: enforced by a test that fails on any memory / injection API |
| Status | Star Wars: Squadrons ✅ triggers, ✅ lightbar | framework + rules + template |

Rules for the online track: [ONLINE_RULES.md on the online branch](../../blob/online/ONLINE_RULES.md).

`main` holds the shared core only. Both tracks build on it, and core fixes land here first and are merged
into both branches.

## Shared core (`dualsense/`)

```
dsx.py        DSX UDP protocol: trigger modes, lightbar RGB, reset
effects.py    GameState -> RT effect (one pulse per shot, adaptive length) and lightbar colour (health)
player.py     XInput trigger read + PlayerPicker (the player's object = the one acting while you press RT)
bridge.py     loop (read -> effects -> DSX), demo reader, CLI
profile.py    builds a DSX controller profile from a game's dsx_profile.toml
```

Requirements: Windows 10/11, Python 3.11+ (stdlib), DSX v3 with *Settings → Networking → Incoming UDP* on.
Tests: `python -m unittest discover tests`.

## Claude Code skill

[`skill/dualsense-for-every-game`](skill/dualsense-for-every-game/SKILL.md) is the full workflow
(choosing the track, finding game state, designing the feel with the player, shipping). Copy the folder
to `~/.claude/skills/` and run `/dualsense-for-every-game`.

## License

MIT
