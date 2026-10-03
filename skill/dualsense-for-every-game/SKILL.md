---
name: dualsense-for-every-game
description: Add DualSense adaptive triggers, lightbar (and haptics, where possible) to a PC game that has no PS5 controller support, driven by live game state read from memory and sent through DSX. Use when the user wants PS5 / DualSense effects in a specific PC game, says "/dualsense-for-every-game", asks to make triggers react to shots / ammo / health in a game, or asks to add a new game to the "Experience Your DualSense Controller in ANY Video Game" framework. Offline play only: games without anti-cheat (single-player branch) or games with online modes and anti-cheat, played only in their offline modes with the anti-cheat switched off (online branch).
---

# DualSense for every game

Goal: a PC game, a DualSense, and DSX. Make the controller react to what happens in the game:
a trigger kick per shot, a lightbar that follows health, and later body haptics. The result is a
`games/<name>/` folder in the framework repo
(https://github.com/RAIZ-Zzz/Experience-Your-DualSense-Controller-in-ANY-Video-Games), on one of two
branches:

- **`single-player`**: single-player games **without** anti-cheat. Hook the game, play.
- **`online`**: games **with** online modes and an anti-cheat (EAC, ...). Supported only in their
  offline modes with the anti-cheat switched off, then restored before any online play. Strict rules in
  `ANTI_CHEAT_RULES.md` on that branch. Star Wars: Squadrons lives here.

Both use the same memory / hook tooling. `main` holds everything shared (`dualsense/`, `tools/`,
`games/_template`, this skill). Fix shared code there and merge `main` into both branches.

The work alternates between you (code, memory analysis) and the user (holding the controller, playing).
Most of the time goes into the loop *user does a scripted thing in game → you measure → you change one
thing*. Plan for that from the start.

## Ground rules

- **Offline only, always.** Never hook a game in an online mode or while its anti-cheat runs, and never
  help disable, hide from or work around an anti-cheat *for online play*. `dualsense/memory.py` refuses
  to attach while an anti-cheat process runs; never remove that guard. For a game with anti-cheat, the
  user chooses to run its offline modes without it (e.g. a documented launcher swap), knows online
  modes stop working, and restores it before playing online.
- **Measure, don't assert.** Every claim about the game (which code runs per shot, fire rate, how the
  controller feels) comes from a run whose real output you show. Assumptions that worked in one mission
  failed in the next (see lessons).
- **The user's hands are the sensor.** You cannot feel the controller. Give the user a short script of
  actions or a test `.bat`, then ask a precise question ("did rounds 1 and 2 feel left vs right?").
- Background recorders: start the recording *before* telling the user what to do, make it long enough
  (2–3 min) for a human to read the message and act, and correlate by timestamps instead of relying on the
  user's timing.
- Things that leave the machine, like pushing to GitHub or installing drivers: confirm first.

## Phase 0: scope and track

Ask, or find out from the files:
1. Game, store / launcher, exact build version (prior work such as CT tables often targets another build).
2. **Anti-cheat?** None → `single-player` branch. Yes → `online` branch, and then:
   - Does the game have offline modes (story, practice, vs AI offline) that work without the anti-cheat?
     If everything worth playing is online-only, stop: the game is not supported.
   - How is the anti-cheat switched off for offline play, and how is it restored (e.g. a store's
     "Repair")? Write both into the game's README; `ANTI_CHEAT_RULES.md` requires it.
3. What the user wants first. Triggers are the most reliable win; lightbar is easy once health is
   known; haptics depend on the output path (Phase 4).

## Phase 1: environment

- DSX v3: *Incoming UDP* on (port in `%LOCALAPPDATA%\DSX\DSX_UDP_PortNumber.txt`, default 6969).
- Virtual device **Xbox 360** for games without DualSense support. Do not switch to a virtual DualSense
  unless the game supports it (it needs a DLC, and it was involved in two BSODs; see lessons).
- **PC crashes or reboots when DSX starts:** read `System` events 41/1001 for the bugcheck, have the user
  copy `C:\Windows\Minidump\*.dmp` from an *admin* shell, parse the driver list (`PAGEDU64` triage dump:
  driver list at the offsets in the header at 0x2000, entries 0x90 bytes, DllBase at +0x38, size at
  +0x48) and find the module containing the faulting address. Known culprit: `steamxbox.sys`. Remove it
  through Steam's UI; never delete the `.sys` by hand (it is a HID class filter, and deleting it leaves
  every keyboard and mouse without a working driver).
- DSX settings belong to the game folder's `dsx_profile.toml`, applied with `dualsense.profile`
  (DSX must be closed: it rewrites its files on exit). Before regenerating, **diff the live profile
  against the generated one**: anything the user changed in the DSX UI must go into the toml first, or
  the apply silently undoes it.

## Phase 2: feel before you hunt

Run `python -m games.<name> --demo` (the generic `DemoReader`) so the user can judge pulse strength,
frequency and resistance before any reverse engineering. Tuning is in `config.toml`.

## Phase 3: find the game state

Target three hooks (see `games/_template/reader.py`): **active** (runs every frame while playing, silent
in menus), **health** (object holds the player's health), **shot** (runs exactly once per shot).

1. **Start from known signatures** (Cheat Engine tables, mods). Executables are often encrypted on disk,
   so scan the *running* process only. `--scan` must report exactly 1 match each.
2. **Register spy** (`dualsense/hook.py`): patch one instruction to jump to a cave that stores the
   object register into a 64-entry ring, runs the stolen bytes, and jumps back. Stolen bytes must be whole
   instructions, at least 5 bytes, with no rip-relative operands. `--probe` prints the objects and values seen.
3. **"Which code changes value X?"**
   - `tools/re/find_writers.py game.exe <offset>` lists every write to `[reg+offset]`. Most belong to
     unrelated classes that share the offset, so keep the ones next to code you already know.
   - Disassemble them (`common.dis`): small functions that add, subtract, or set the field.
   - Hook every candidate function entry with `tools/re/count_calls.py`, have the user do a scripted
     sequence (idle, taps, hold to empty, recharge, switch power), then match call counts to events.
     Squadrons: 260 player shots = 260 calls of exactly one function. The other four never ran.
   - Function only reachable through a vtable: `tools/re/retspy.py` gives the callers.
4. **Player vs everyone else.** Shared code runs for AI too. Never pick "the most frequent object": that
   held in a quiet test mission and broke in a busy one. Use `PlayerPicker`: the object whose code
   runs while the player holds the button (XInput RT of DSX's virtual pad).
5. **Prefer an event hook to a threshold.** Inferring shots from an energy drop needs a threshold that
   differs per ship and weapon; the per-shot function does not.
6. **Robustness:** the game may be starting (code not decrypted yet) or closing (memory gone) when the
   bridge attaches. That must become `GameNotReady` and a retry, never a crash. Restore patched code on
   exit.

## Phase 4: design the feel with the user

Iterate one variable at a time; show a frame-by-frame trace (e.g. `#` per 5 ms of pulse) of what the
code will do before the user tests it.

Trigger physics that decide the design:
- **Resistance** is felt only while the finger *moves* through the zone. A held trigger feels nothing,
  so a resistance "kick" per shot is useless during held fire.
- **Vibration modes** (`AUTOMATIC_GUN`) are time-based, so use them for events. Position-based modes
  (semi-auto, weapon) cannot be synced to a shot.
- A free-running vibration ("machine gun") is not synced to the game's fire rate, and users notice.

What the first user settled on (Squadrons), which is a good default:
- One pulse per shot, same strength. Pulse = min(0.12 s, half the gap since the previous shot), at least
  20 ms of rest between pulses (cut a running pulse rather than delay the next). Loop 200 Hz.
- Light constant resistance between shots (force 1), the same at every energy level. LT untouched.
- Lightbar hue green → yellow → red (HSV, not an RGB fade, which passes through dark olive), eased;
  a hit snaps to red and eases back in one movement; pulsing below 25 % for colour-blind readability.
- Gyro to stick was rejected: the game has no gyro support, so it has no recentering.

Haptics (body vibration). Know the output paths before promising anything:
- **Game rumble through Xbox emulation:** DSX maps left motor = heavy, right = light. Balanced
  left/right is impossible on this path (left 8 % still beat right 100 %). Per-side intensity only
  shifts the balance a little.
- **DSX UDP** exposes triggers, LEDs, player LEDs and reset. As far as known, there is no instruction
  for the haptic actuators.
- **Audio → haptics (DSX+ Bluetooth):** stereo, but it captures the system output, so anything you play
  is audible, and its level follows Windows volume (measured −26 dB with a low Windows volume). Test with
  `tools/haptics/tone_test.py` (DSX running!). Check whether game sounds are already panned per side
  with `tools/re/audio_pan.py`. In Squadrons they were, but only about ±0.1.

## Phase 5: ship

- `games/<name>/` from the template, README with build version, how the hooks were found, and the
  measured numbers.
- Tests: pure logic (effects, picker), the hook executed in the test process itself (catches encoding
  and off-by-one bugs; it caught two), and "game closing" fakes.
- `python -m unittest discover tests` must pass before committing.

More detail, numbers and the mistakes made along the way: [references/lessons.md](references/lessons.md).
