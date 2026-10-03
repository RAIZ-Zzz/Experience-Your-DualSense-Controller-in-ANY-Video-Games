---
name: dualsense-for-every-game
description: Add DualSense adaptive triggers, lightbar (and haptics, where possible) to a PC game that has no PS5 controller support, driven by live game state read from memory and sent through DSX. Takes the game's install folder as its argument ("/dualsense-for-every-game D:\Games\MyGame"); asks for it first if missing. Use when the user wants PS5 / DualSense effects in a specific PC game, says "/dualsense-for-every-game", asks to make triggers react to shots / ammo / health in a game, or asks to add a new game to the "Experience Your DualSense Controller in ANY Video Game" framework. Offline play only: games without anti-cheat (single-player branch) or games with online modes and anti-cheat, played only in their offline modes with the anti-cheat switched off (online branch).
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

## Input: the game's install folder

The skill needs exactly one input: the folder the game is installed in (the one holding its `.exe`).
If the user did not give it, ask for it and do nothing else until you have it. Everything else (name,
build, store, engine, anti-cheat, genre) you find out yourself in Phase 0; ask the user only what the
folder and the web cannot answer.

## Ground rules

- **Offline only, always.** Never hook a game in an online mode or while its anti-cheat runs, and never
  help disable, hide from or work around an anti-cheat *for online play*. `dualsense/memory.py` refuses
  to attach while an anti-cheat process runs; never remove that guard. For a game with anti-cheat, the
  user chooses to run its offline modes without it (e.g. a documented launcher swap), knows online
  modes stop working, and restores it before playing online.
- **Measure, don't assert.** Every claim about the game (which code runs per shot, fire rate, how the
  controller feels) comes from a run whose real output you show. Assumptions that worked in one mission
  failed in the next (see lessons). In universal-modder's words: *the running game is the oracle; your
  reading of the code is not.*
- **Circuit breaker** (from universal-modder): after three identical failures, stop, write the dead end
  into `MODLOG.md`, and change approach instead of retrying.
- **Keep a `MODLOG.md`** (from universal-modder) in the game folder from the first minute: paths,
  addresses, real outputs, dead ends, next step. It becomes the README and the lessons at the end.
- **The user's hands are the sensor.** You cannot feel the controller. Give the user a short script of
  actions or a test `.bat`, then ask a precise question ("did rounds 1 and 2 feel left vs right?").
- Background recorders: start the recording *before* telling the user what to do, make it long enough
  (2–3 min) for a human to read the message and act, and correlate by timestamps instead of relying on the
  user's timing.
- Things that leave the machine, like pushing to GitHub or installing drivers: confirm first.
- **The game's install folder is read-only for you.** Never write, copy or generate anything into it.
  Files go by kind:
  - user-facing scripts (`start.bat`, `demo.bat`, `config.toml`, reader): the game module in the
    studio, `studio/tracks/<track>/games/<module>/`;
  - research runs worth re-running on the next build: its `research/` subfolder;
  - throwaway probes, logs and dumps: a scratch folder outside both the repo and the game.
  The only change to the game's files is the anti-cheat switch on the `online` track, which the user
  does by following the README; you write the steps, not the files.
- **Announce every hook before it goes in.** Before anything patches the game's memory (`--scan` only
  reads; `--probe`, `count_calls.py`, `retspy.py`, `audio_pan.py`, `start.bat` patch), tell the user:
  which code is hooked and why, that the game must be in an offline mode with the anti-cheat off, that the
  patch is removed on exit, and what could go wrong (a crash of the game, no lasting change). Wait for a
  yes. One yes covers re-running the same hook, not a new one.

## Phase 0: audit, research, proposal

Do steps 1–2 on your own, without asking the user, and without touching the game (it need not run).

1. **Audit the install folder** (read only). Report what you found and how you know it:
   - Main executable(s), size, version resource, `tools/evidence.py` hashes.
   - Store: `steamapps/appmanifest_*.acf` above the folder (Steam), `__Installer/` (EA app),
     `.egstore/` (Epic), `goggame-*.info` (GOG).
   - Engine: `*.pak` + `Engine/` (Unreal), `*_Data/` + `UnityPlayer.dll` (Unity), `*.sb`/`*.toc` (Frostbite),
     `re_chunk_*.pak` (RE Engine), `archive/pc/` (REDengine)...
   - **Anti-cheat**: `EasyAntiCheat/`, `*_eac.exe`, `BattlEye/`, `*BE.exe`, `vgk`, `mhypbase.dll`...
     None → `single-player` track. Present → `online` track, see step 2.
   - Mod loaders already installed (`dinput8.dll`, `version.dll`, `ScriptHookV.dll`, `UE4SS/`,
     `BepInEx/`, `reframework/`) and save location.
2. **Research the game on the web**: genre and how it plays, official telemetry, existing mods and
   CT tables for this build, and (online track) whether offline modes exist and how others run them
   without the anti-cheat and restore it. If everything worth playing is online-only, stop: the game is
   not supported. Then collect what the effects will be built on, by genre:
   - **Shooter**: the full weapon list, sorted into classes by how they fire: automatic (machine gun,
     SMG, assault rifle), semi-auto (pistol, DMR), single heavy shot (sniper, shotgun, launcher),
     draw-and-release (bow, crossbow), charge (energy, railgun), melee. Note fire rates where known.
   - **Action / racing / flight**: what the triggers are for (attack, brake, throttle) and what state
     drives them (stamina, speed, ABS, overheat).
   - **Exploration / casual**: what is worth feeling (footsteps, terrain, interactions) and showing
     (health, time of day, area). Here haptics and lightbar matter more than triggers.
3. **Propose the design** and let the user choose before writing any code. Write it as a short list of
   options per effect, each with what the user will feel and what it costs to build. For a shooter, one
   trigger profile per weapon class, e.g.:
   - automatic → one `AUTOMATIC_GUN` pulse per real shot + light `RESISTANCE` (the Squadrons default);
   - semi-auto → `SEMI_AUTOMATIC_GUN` click;
   - heavy single shot → `WEAPON` / hard `RESISTANCE` with a strong kick;
   - bow → `BOW` (tension grows with draw);
   - charge → rising `RESISTANCE`, `VIBRATE_TRIGGER` when full;
   plus the lightbar source (health, ammo, team colour) and what haptics can and cannot do (Phase 4).
   Also say up front that on-screen button prompts stay Xbox (the game sees DSX's Xbox 360 pad); check in
   step 2 whether the game ships PlayStation prompts at all, so the user knows if a later UI mod is
   even possible.
   Say which game state each option needs, and whether that state needs a hook (Phase 3) or comes from
   telemetry / an existing mod. Recommend one option per effect; the user picks, then `studio.py new`.
4. **Route.** Take the cheapest route that reaches the effect, and write in `MODLOG.md` why the cheaper
   ones don't work (ladder adapted from universal-modder's route selection; the rungs are what existing
   DualSense mods use, see `references/prior-art.md`):
   1. **Official telemetry**: the game streams its state by itself (Forza's UDP "data out", as used by
      ForzaDSX).
   2. **An existing script hook / mod loader** for that game or engine: ScriptHook (RDR2 – DSX),
      Cyber Engine Tweaks (Cyberpunk's DualSense mods), REFramework (RE4 Remake triggers), UE4SS,
      BepInEx... The community already maps the game's state there.
   3. **External hooks with this framework** (`dualsense/hook.py`): when nothing above exists, as for
      Star Wars: Squadrons.

## Phase 1: environment

- **Backups first** (from universal-modder): before the first modded launch, back up the game's saves
  and write the restore path into `MODLOG.md`. On the `online` branch also write down how the
  anti-cheat is restored.
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

Every step below that patches memory needs the hook announcement and the user's yes (ground rules).

Target three hooks (see `games/_template/reader.py`): **active** (runs every frame while playing, silent
in menus), **health** (object holds the player's health), **shot** (runs exactly once per shot).

0. **Evidence record** (from the awesome-game-security reverse-engineering skill): `python
   tools/evidence.py <exe>` → size and SHA-256 of the exact build into the README's *Evidence* table.
   For every finding, say whether it is *runtime evidence* (call counts, values seen in the running game)
   or *static inference* (only read from code), and label uncertainty caused by protection (e.g. an
   encrypted executable whose code exists only at runtime).
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
   - Save each run that found something as `games/<name>/research/*.bat` (the exact command and
     addresses, result in a comment), so the next build can be checked by re-running them.
4. **Player vs everyone else.** Shared code runs for AI too. Never pick "the most frequent object": that
   held in a quiet test mission and broke in a busy one. Use `PlayerPicker`: the object whose code
   runs while the player holds the button (XInput RT of DSX's virtual pad).
5. **Prefer an event hook to a threshold.** Inferring shots from an energy drop needs a threshold that
   differs per ship and weapon; the per-shot function does not.
6. **Robustness:** the game may be starting (code not decrypted yet) or closing (memory gone) when the
   bridge attaches. That must become `GameNotReady` and a retry, never a crash. Restore patched code on
   exit.

## Phase 4: design the feel with the user

**Vertical slice first** (from universal-modder): one effect working end to end in the real game before
the next. In Squadrons: RT pulse per shot, then the lightbar, then haptics.

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
- Next idea, not built yet: **per-weapon trigger profiles**, as RDR2 – DSX and Cyberpunk's DualSense mods
  do (a trigger mode per weapon type). In Squadrons the weapon data pointer is `[obj+0x388]` of the
  shot object. Cyberpunk's mod also moved automatic weapons to the *real attack speed*, the same
  conclusion as our one-pulse-per-real-shot design.

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

- Work in the studio (see the repo README): `python core/tools/studio.py new <name> --track <track>` creates
  `games/<module>/` on that track's branch (`studio/tracks/<track>/`) with a `TASKS.md`. Keep `Status:` /
  `Next:` and the checklist in TASKS.md current; `studio.py` turns them into the STUDIO.md dashboard. Core
  changes go to `main` first, then `studio.py sync`.
- Release for players (public: confirm first): a zip of only what runs, from the track worktree,
  `git archive --prefix=<name>-dualsense/ -o <name>-dualsense.zip HEAD LICENSE dualsense games/__init__.py
  games/<module> ':!games/<module>/research' ':!games/<module>/TASKS.md'`, then
  `gh release create <name>-v<x.y> <zip> --target <full 40-char SHA> --notes-file notes.md` (a short SHA
  is rejected), and link it in the main README's games table.
- `games/<name>/` from the template, named after the full game (`star_wars_squadrons`). README sections:
  *Evidence*, (online branch) *Anti-cheat off* / *Restore the anti-cheat*, *How the hooks were found*,
  *Measured*. This is the field note that universal-modder writes at the end: `MODLOG.md` condensed.
- Add the game to the main README's *Games that have been applied with the skill* table, with a photo of the effect if the user has
  one (`docs/images/`).
- Tests: pure logic (effects, picker), the hook executed in the test process itself (catches encoding
  and off-by-one bugs; it caught two), and "game closing" fakes.
- `python -m unittest discover tests` must pass before committing.

More detail, numbers and the mistakes made along the way: [references/lessons.md](references/lessons.md).
Where the borrowed ideas come from, and what was deliberately not borrowed:
[references/prior-art.md](references/prior-art.md).
