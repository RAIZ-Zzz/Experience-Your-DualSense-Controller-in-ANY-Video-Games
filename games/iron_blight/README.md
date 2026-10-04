# Iron Blight

Steam build **25439780** (appid 4001350), PC. Single-player only, no anti-cheat.
Unity 6000.3.15f1, IL2CPP.

- **RT:** one pulse per real shot plus a kick of the right grip, per weapon (pistol light ... shotgun
  heaviest); light constant resistance between shots; a plain, slack trigger when the gun can't fire
  (no gun in hand, holstering, empty, jammed, reloading, mag check). LT untouched.
- **Kick / melee:** a grip rumble at the moment the blow lands, not at the button press.
- **Lightbar:** player health, green → yellow → red, red flash on a hit, pulsing below 25 %.

Felt in the game so far: the pistol (TT-33), the kick and melee swings. The other weapons use first-guess
strengths in `config.toml` (`[weapons.*]`); tune them there.

## Setup

Requirements: Windows, Python 3.11+ (standard library only), DSX v3 with *Incoming UDP* on.

1. If DSX is not installed at `D:\steam\steamapps\common\DSX\Main_v3_Beta`, put your DSX folder in
   `dsx_profile.toml` → `dsx_dir`.
2. Close DSX, run `apply-dsx-profile.bat` (writes the DSX profile "Iron Blight": virtual Xbox 360 pad,
   Xbox rumble → haptics; backs up the old one as `.dsx.bak`), start DSX.
3. `install.bat`: from now on it runs in the background (no window) from Windows logon, waits for the
   game and attaches by itself; just start the game. While the game is not running it sends nothing to
   DSX and looks for the game every 3 s. The first attach takes about 40 s (it scans the game's memory
   for the classes once). Log: `%TEMP%\dualsense_iron_blight.log`. `uninstall.bat` stops it and removes it
   from logon. Without installing: `start.bat` before or after the game.

`demo.bat` lets you feel the effects without the game.

## Evidence

| File | Size | Date | SHA-256 |
|---|---|---|---|
| `Iron Blight.exe` | 667648 | 2026-10-02 | `c4e419111626ff9920186ad2683e01a13c0671ac52ff9bf789bde3e551325527` |
| `GameAssembly.dll` | 66202112 | 2026-10-02 | `bcc1740d2b75b82560fa1c76c22310c21ad78928166fd311a0dd7de7036e40fe` |
| `global-metadata.dat` | 13989020 | 2026-10-02 | `c5bae9eacbbeb610f66ef7817f703ef8e4c0a325df584ad68ec8d72f70e6f301` |

- **Runtime evidence** (seen in the running game with `watch.bat`): all four classes below found; pistol
  `ammoCount` 9 → 0, exactly −1 per shot, in lockstep with the game's own `shotCount`; `isJammed` set by a
  jam and cleared by the clearing action; reload and mag check change no ammo count into a shot;
  holstering nulls `GunHandler.instance`; `canKickLand` turns True 0.42 s after the kick press;
  air melee swings don't change the melee weapon's `ammoCount`.
- **Static inference** (read from the metadata only): the `gunType` enum order beyond value 0 (pistol);
  that the shotgun also uses one round per shot; that `canMeleeAttackLand` is the hit moment, like the kick.

## How the state was found

No hooks and no writes: the bridge only reads memory. `dualsense/il2cpp.py` parses the game's
`global-metadata.dat` (v39, not encrypted; upstream Il2CppDumper doesn't support v39), then finds the
classes, their field offsets and static singletons by name in the running game. An update that keeps the
names keeps working.

| Object | Fields read |
|---|---|
| `Player.instance` | `health`, `baseHealth`, `IsDead`, `isKicking`, `canKickLand` |
| `MainMenu.instance` | `isPaused` |
| `GunHandler.instance` | `currentGun`, `isSelected`, `isReloading`, `isCheckingAmmo`, `isMeleeAttacking`, `canMeleeAttackLand` |
| `currentGun` (`Gun`) | `ammoCount`, `gunType`, `isJammed`, `isMelee` |

A shot is the selected gun's `ammoCount` dropping while it is not being reloaded or checked. Polling
is enough here because ammo is an integer per gun: the fastest gun (MP5, ~13 shots/s) fires 75 ms apart,
the read loop runs every 5 ms.

## Measured

- Pistol: 9 shots = 9 rounds = 9 `shotCount`; the 3rd shot jammed (ammo stayed 6 until cleared).
- Kick: wind-up 0.42 s from the press to `canKickLand`; the rumble was first sent at the press and felt
  too early, so it now fires at `canKickLand`.
- Melee: `canMeleeAttackLand` 0.10-0.61 s after the swing starts.
- Holster: ~1 s of `isSelected False` + `isHolstering True` before the gun is put away.

## Files

`install.bat` / `uninstall.bat` run in the background from logon, or stop · `start.bat` play once · `demo.bat` feel without the game · `watch.bat` print the values read (nothing sent to
DSX; also logged to `%TEMP%\iron_blight_watch.log`) · `apply-dsx-profile.bat` write the DSX profile
(DSX closed) · `config.toml` strengths per weapon · `states.py` / `states.json` every game state simulated
and checked against the design rules (`python -m games.iron_blight --states`).
