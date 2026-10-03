# Online track rules

Games played online have anti-cheat, terms of service, and other players. A controller mod must never be
mistaken for a cheat, and it must never be one. On this branch:

## Never

1. **Open the game process.** No `OpenProcess`, no reading or writing its memory, not even "read-only" or
   "just to find an address".
2. **Inject anything.** No DLLs, code caves, hooks, detours, or renderer / overlay hooks inside the game.
3. **Touch the anti-cheat.** Do not disable, bypass, hide from, or work around it, and do not run the
   game in a mode meant to avoid it.
4. **Use kernel drivers or debuggers** against the game.
5. **Give an advantage.** No effect may reveal information the player could not otherwise perceive (e.g.
   "trigger buzzes when an enemy is behind you" from data the game doesn't show).

`tests/test_online.py` fails the build if any of the APIs behind 1, 2 and 4 appear in the code.

## Allowed sources

| Source | Examples | Notes |
|---|---|---|
| Official telemetry / game-state APIs | F1 / Forza / Assetto Corsa UDP telemetry; Valve Game State Integration (CS2, Dota 2) | The game sends the data itself, on purpose. Preferred. Use `dualsense/telemetry.py`. |
| The player's own input | XInput trigger / buttons of DSX's virtual pad (`dualsense/player.py`) | Shows when the player pulls, not what the game did. |
| The PC's audio output | WASAPI loopback of your speakers (e.g. gunshot onsets) | Reads your sound device, never the game. |

## Ask first

- **Screen capture** of the game window (reading the HUD): tolerated by some games, flagged by others.
  Only with the user, after checking that game's rules.
- **Virtual controller drivers** (DSX's Xbox / DS4 emulation): widely used, but a few games block them.
  If a game refuses the virtual pad, stop. Never try to hide the driver.

## When in doubt

Don't. Ship the effect for single-player on the `single-player` branch instead, or ask the game's
developer whether a telemetry / game-state API exists.
