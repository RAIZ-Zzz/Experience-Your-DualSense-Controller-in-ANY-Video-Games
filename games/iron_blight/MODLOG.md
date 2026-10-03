# MODLOG: Iron Blight

Working journal while adding this game: append as you go, newest at the bottom. When the game works,
turn it into the README sections (*Evidence*, *How the hooks were found*, *Measured*) and the skill's
lessons. (Idea: universal-modder's MODLOG.md and "field note", see skill/.../references/prior-art.md.)

## Scope
- Game / store / build: Iron Blight (Ronesans Interactive, released 2026-08-24), Steam appid 4001350,
  buildid 25439780, install `B:\SteamLibrary\steamapps\common\Iron Blight`.
  Unity 6000.3.15f1 (c1aa84e375f6), IL2CPP (`GameAssembly.dll`), metadata `AF1BB1FA` v39, not encrypted.
- Anti-cheat: none (no EAC/BattlEye files; Steam page: single-player only) → `single-player` branch.
- Definition of done: RT gives one pulse per real shot with a per-weapon feel, goes slack when the gun is
  empty or jammed, and the lightbar follows the player's health.

## Evidence (tools/evidence.py, 2026-10-04)
| File | Size | Date | SHA-256 |
|---|---|---|---|
| `Iron Blight.exe` | 667648 | 2026-10-02 | `c4e419111626ff9920186ad2683e01a13c0671ac52ff9bf789bde3e551325527` |
| `GameAssembly.dll` | 66202112 | 2026-10-02 | `bcc1740d2b75b82560fa1c76c22310c21ad78928166fd311a0dd7de7036e40fe` |
| `global-metadata.dat` | 13989020 | 2026-10-02 | `c5bae9eacbbeb610f66ef7817f703ef8e4c0a325df584ad68ec8d72f70e6f301` |

## Route
- Chosen: external hooks (this framework), function addresses located by IL2CPP method names.
- Why the cheaper routes don't work:
  - Official telemetry: none.
  - Mod loader: none installed and no community mod for this game; BepInEx/MelonLoader would need files
    in the game folder, and their Unity 6000.3 IL2CPP support is unverified.
- Core change needed: `dualsense/memory.py` scans/hooks only the main module, which here is a 667 KB stub;
  the game code is in `GameAssembly.dll`.

## Static inference (metadata strings only, not yet seen running)
- Candidate shot code: `ShootGun`, `TryShoot` (also `jammedTryShoot`, `reloadingTryShoot`), `OnFire`.
- Empty / jam: `GunEmpty`, `JamGun`, `IsCantFireAnim`. Fire mode: `ChangeFireMode`.
- Health: `TakeDamage`, `DamagedPlayer`, `GetHealthColor`, `green/yellow/orangeHealthThreshold`.
- Current weapon: `GunHandler`, `currentGun`, `currentGunObject`.
- Ammo fields per gun type: pistol, revolver, smg, pp91, sr3m, boltAction, doubleBarrel, pumpAction,
  assaultRifle (more than the 6 weapons the fan wiki lists: TT-33, MP5, shotgun, Magnum, melee, kick).
- No game-specific rumble calls found (only Unity Input System's `SetMotorSpeeds` etc.).
- `PS4_*` names are Steamworks input-origin enums, not game button prompts: prompts stay Xbox/keyboard.
- Gamepad: devs wrote in patch 1.05 that Xbox gamepad support comes "in a later patch"; players use
  Steam Input mapped to keyboard/mouse. Not yet tested here.

## Design chosen by the user (2026-10-04)
- RT: per-weapon profiles + empty/jam: jammed (and empty) → resistance off. LT untouched.
- Lightbar: health colour green → yellow → red, hit flashes red, pulse below 25 %.
- Haptics: not now.

## Backups / restore
- Saves: `%USERPROFILE%\AppData\LocalLow\Ronesans Interactive\Iron Blight\` (only Player.log on
  2026-10-04; the user has not played yet). Back up before the first hooked launch.
- DSX profile backup: `<profile>.dsx.bak` (written by apply-dsx-profile)

## Log
<!-- date - what was tried - real output - conclusion. Dead ends too; stop after 3 identical failures. -->
- 2026-10-04 - Phase 0 audit + research done, design chosen. `studio.py new "Iron Blight"` made a folder
  with a space; renamed to `iron_blight` and fixed `studio.py` on main (273f95a).
