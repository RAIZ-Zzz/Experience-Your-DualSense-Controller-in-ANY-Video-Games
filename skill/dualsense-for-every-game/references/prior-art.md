# Prior art: what this skill borrows, and from whom

Every idea taken from another project is listed here with what was taken and where it now lives in
this skill or repo. Ideas this project arrived at on its own, but which match earlier work, are listed
too (marked *convergent*), so nobody mistakes them for borrowed or original.

## Agent skills for modding / reverse engineering

### rehan-remade/universal-modder
<https://github.com/rehan-remade/universal-modder> (`skills/mod-any-game/SKILL.md`): a Claude Code
skill set for modding PC games: intake → recon → route → lab (backups) → source of truth → vertical
slice → assets → verify in the real game → showcase → publish → field note.

Taken:
- **Route ladder**: pick the cheapest route that reaches the idea, and write down why: data only →
  existing mod loader → managed patching → native hooks. Adapted here as: official telemetry → the
  game's existing script hook / mod loader → our external hooks (SKILL.md, Phase 0 "Route").
- **MODLOG.md, then a field note**: a working journal per game (paths, IDs, failures, next steps) that is
  turned into a knowledge entry at the end. Here: `games/_template/MODLOG.md`, then the game README's
  *How the hooks were found* / *Measured* and `references/lessons.md`.
- **Backups first**: back up saves and record the restore path before any modded launch (Phase 1).
- **"The running game is the oracle; your reading of the code is not."** Matches our *measure, don't
  assert* rule; the wording is theirs.
- **3-strike circuit breaker**: after three identical failures, stop, document the dead end, pivot.
- **Vertical slice**: one feature end to end in the real game before widening scope (Phase 4: RT pulse
  per shot first, lightbar second, haptics last).

Not taken: their guardrail is stricter on anti-cheat: *never bypass anti-cheat, DRM or ownership
checks; if offline launch is required, use the official option*. This repo's `online` branch instead
switches an anti-cheat off for offline modes only, by a documented, reversible method, and restores it
before online play (`ANTI_CHEAT_RULES.md`). That is the project owner's decision; it is stated here so
the difference is visible.

### gmh5225/awesome-game-security: reverse-engineering skill
<https://github.com/gmh5225/awesome-game-security/blob/main/.claude/skills/reverse-engineering/SKILL.md>

Taken:
- **Record artifact hash, format, architecture, tool version, environment and observed addresses.**
  Here: `tools/evidence.py` and the *Evidence* table in every game README.
- **Separate static inference from runtime evidence, and label uncertainty** caused by protection
  (e.g. an encrypted executable). Here: game README *Evidence* section and Phase 3.

### vgrichina/re-skill
<https://github.com/vgrichina/re-skill>: a Claude Code skill that scaffolds a reverse-engineering
workspace for retro ROMs and iterates disassemble → annotate. Not used directly (it works on ROMs, not
live PC processes). Listed as related work.

## DualSense mods built on DSX

Pattern shared by all of them: *get game state → choose a trigger effect → JSON over UDP to DSX on
127.0.0.1:6969*. That is also this repo's architecture (*convergent*).

- **ForzaDSX** (<https://github.com/cosmii02/ForzaDSXlegacy>, originally
  <https://github.com/patmagauran/ForzaDualSense>): uses Forza's official UDP "data out" telemetry.
  Taken: telemetry as the first rung of the route ladder.
- **RDR2 – DSX / DualSense4Rockstar** (<https://github.com/Shtivi/RDR2-DualSense>,
  <https://github.com/Killface1980/DualSense4Rockstar>): run inside the game through ScriptHook, with a
  trigger mode per weapon type. Taken: "existing script hook" as the second rung; per-weapon trigger
  profiles as a future step (the weapon data pointer in Squadrons is `[obj+0x388]`).
- **Cyberpunk 2077 – Enhanced DualSense Support** (<https://www.nexusmods.com/cyberpunk2077/mods/4156>):
  runs through Cyber Engine Tweaks; its changelog moved automatic weapons to *tracking the real attack
  speed instead of hardcoded values*. *Convergent* with our one-pulse-per-real-shot design, which the
  first user arrived at after rejecting a free-running "machine gun" vibration.
- **Resident Evil 4 Remake adaptive triggers** (<https://www.nexusmods.com/residentevil42023/mods/5813>):
  uses REFramework to track the current weapon and magazine ammo. Taken: engine frameworks (REFramework,
  UE4SS, BepInEx...) belong on the second rung before writing raw hooks.
- **DSX / DualSenseX** (<https://github.com/Paliverse/DualSenseX>): the UDP protocol, and its warning
  that community mods must not be used in online games. Reflected in `ANTI_CHEAT_RULES.md`.

## Tools referenced

- Cheat Engine tables by FearLess / N3rveMods for Star Wars: Squadrons: the first two code signatures.
- PCGamingWiki: the documented launcher-rename method used to run Squadrons' offline modes without EAC.
- capstone (disassembly), soundcard + numpy (loopback audio): analysis tools only.
