# Experience Your DualSense Controller in ANY Video Game: online track

**Branch `online`**: for games played online, with their anti-cheat running. The game's memory is
**never opened**. Game state comes only from sources the game allows: its own telemetry / game-state
API, your controller input, or your PC's audio output. Read [ONLINE_RULES.md](ONLINE_RULES.md) first.

For offline / single-player games (memory hooks allowed), use the [`single-player`](../../tree/single-player)
branch; [`main`](../../tree/main) explains both tracks.

> `tests/test_online.py` scans every Python file and fails if any process-memory, injection or
> debugging API shows up. Keep it green; never weaken it.

## Status

Framework, rules and template. No game yet: the first candidates are games with official telemetry
(racing games' UDP "data out", Valve's Game State Integration).

## Layout

```
dualsense/            shared core (from main) + online parts:
  telemetry.py        UdpTelemetryReader: subclass, implement parse(packet) -> GameState
games/_online_template/   start here for a new online game
ONLINE_RULES.md       what is never allowed, what is allowed, what to ask first
tests/                python -m unittest discover tests (includes the guard)
```

## Adding a game

1. Check `ONLINE_RULES.md` and find an allowed source for the game.
2. Copy `games/_online_template`, implement `parse()` from the game's published packet format.
3. `demo.bat` to tune the feel, `start.bat` to play.

The full workflow is in the Claude Code skill: [`skill/dualsense-for-every-game`](skill/dualsense-for-every-game/SKILL.md).

## License

MIT
