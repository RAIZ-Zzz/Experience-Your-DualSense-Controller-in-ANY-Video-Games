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
- Chosen: **read-only memory polling, no hooks** (user's call 2026-10-04): `dualsense/il2cpp.py` finds
  classes, field offsets and static singletons by name in the running game; hooks only as a fallback for a
  state that has no field.
- Why the cheaper routes don't work:
  - Official telemetry: none.
  - Mod loader: none installed and no community mod for this game; BepInEx/MelonLoader would need files
    in the game folder, and their Unity 6000.3 IL2CPP support is unverified.
- Why no dumper: metadata v39 is not supported by upstream Il2CppDumper (only third-party forks). The
  runtime resolver needs none and survives updates that keep the names.
- Why polling is enough here (unlike Squadrons' energy): ammo is an integer per gun, one round per shot;
  MP5 ~13 shots/s = 75 ms apart vs a 5 ms read loop.

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
- 2026-10-04 - Parsed metadata v39 by hand (header = 31 (offset, size, count) triples; typedef 76 bytes,
  field 10 bytes, method 30 bytes). Static inference, to be checked with `watch.bat`:
  - `Player`: static `instance`; `health`, `baseHealth`, `<IsDead>k__BackingField` (MonoBehaviour)
  - `GunHandler`: static `instance`; `currentGun`, `isReloading`, `isCheckingAmmo`, `shotCount` (MonoBehaviour)
  - `Gun` (: AbstractInventoryItem, no subclasses): `ammoCount`, `gunType`, `isJammed`, `isJammedThisMag`,
    `isMelee`, `isAutomatic`, `isPumpAction`, `isRevolver`, `rof`, `projectilesPerShot`
  - `MainMenu`: static `<instance>k__BackingField`; `isPaused`
  - enum `Type` (gunType): pistol, shotgun, smg, rifle, revolver, melee, assaultRifle (values assumed 0..6)
- 2026-10-04 - Reader written (read-only), core il2cpp.py tested against a fake process only.
  To verify in the game: classes found at all and how long the scan takes; `ammoCount` drops by exactly 1
  per shot (also shotgun) and not on reload/mag check; `isJammed` vs `isJammedThisMag`; gunType values;
  `shotCount` as a cross-check.
- 2026-10-04 02:10-02:13 - First `watch.bat` run in the real game (runtime evidence; user played the prologue
  to the TT-33, fired, jammed, reloaded, checked the mag, paused):
  - All four classes found read-only on Unity 6000.3; GunHandler/Gun picked up by the 10 s rescan once the
    player had a gun (`gun: None` before).
  - `paused` follows the pause menu; `health 80.0 / baseHealth 100.0`; `dead False`. No hit seen yet.
  - Pistol: `ammoCount` 9 → 0, exactly -1 per shot, `shotCount` +1 in lockstep (9 shots = 9 + 9).
    `gunType` 0 = pistol (enum order confirmed for value 0 only).
  - Jam: the 3rd shot set `isJammed True` (ammo 6); clearing it shows `isReloading True`, then
    `isJammed False` with ammo still 6. `isJammed` is the right field.
  - Reload: `isReloading True`, ammo 0 → 8 inside it; mag check: `isCheckingAmmo True`, ammo unchanged.
    Neither would count as a shot.
  - Odd: shots 8 and 9 were 11 ms apart (02:13:05.541 / .552), both counted by the game's own `shotCount`.
    Asked the user whether that was a double tap.
