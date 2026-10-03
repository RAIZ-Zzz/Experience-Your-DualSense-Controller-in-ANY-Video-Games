# Star Wars: Squadrons

EA app build **1.0.10.39591**, PC. Single-player only: Story and Practice.

<img src="../../docs/images/star-wars-squadrons-lightbar.png" width="420" alt="DualSense lightbar turning yellow as the TIE fighter's hull drops">

*The lightbar follows the hull: yellow here after taking damage in a TIE fighter.*

## Evidence

| File | Size | Date | SHA-256 |
|---|---|---|---|
| `starwarssquadrons.exe` (the game) | 463792960 | 2026-09-29 | `83a55a3987f58d87551209670f5b913b245d978bac34d76193c3d502a9172467` |
| `starwarssquadrons_launcher_eac.exe` (original EAC launcher) | 1135232 | 2026-09-29 | `b157b97091de251211f27a91a47a736eb784ee739ef08b3f1a275731770eb7a5` |

The exe is encrypted on disk (EA DRM, `.ooa` section): every signature and address below exists only in
the running game, so the hooks can only be checked at runtime (`scan.bat`).

- **Runtime evidence** (seen in the running game): the three signatures match exactly once; `shot` ran
  260 times for 260 player shots, also at "empty"; the other four energy functions never ran while
  firing; one caller of `shot`; energy 182/182 and hull 1200/1200 at full; held fire 0.13–0.17 s apart;
  in a busy mission the energy tick sees several ships (330 calls/s).
- **Static inference** (read from code only): what the four unused energy functions are for (pay
  pending, drain by fraction, add by fraction, set); that the weapon data at `[obj+0x388]` holds the
  per-shot cost.

## Anti-cheat off (offline only)

The game refuses memory access while EasyAntiCheat runs, and so does this bridge. The launcher-rename
method from [PCGamingWiki](https://www.pcgamingwiki.com/wiki/Star_Wars:_Squadrons) works with the EA app:
the EAC bootstrapper `starwarssquadrons_launcher.exe` is renamed away and replaced by a copy of
`starwarssquadrons.exe` (which must stay too: the installer manifest lists it). Launch from the EA app as
usual. Only Story and Practice work; online modes kick you without EAC.

## Restore the anti-cheat

Before playing online: EA app → Star Wars: Squadrons → *Repair*. It restores the original launcher
(a game update does the same). Close `start.bat` first.

## What is hooked

| Hook | Code | Object | Fields |
|---|---|---|---|
| `energy` | per-frame weapon-energy tick (`movss xmm0,[rbx+3D0]`) | rbx | used only as "in flight" |
| `health` | hull read (`movaps xmm6,xmm0; mov rax,[rcx]`) | rcx | `+0x20` / `+0x24` cur / max |
| `shot` | weapon's "pay for one shot" virtual method, entry | rcx | energy `+0x2E0` / `+0x3D0` |

How `shot` was found: 112 instructions write `+0x2E0`; 8 sit next to the energy tick; they form 5 tiny
functions (subtract cost, subtract fraction, add fraction, pay pending, set). Hooking all 5 while firing:
only one ran: 260 calls for 260 player shots (519 more for AI ships), including single shots
fired at "empty". It is reached through a vtable (slot `0x1436a68c8`) from one caller (`0x1417b4c0b`).

Measured: held fire 0.13–0.17 s between shots (about 6.7/s), one shot costs 3.0 of 182 energy.
In bigger missions many ships run the same code, so the player's ship is picked by RT correlation.

## Research scripts (`research/`)

How the hooks above were found, re-runnable on this build (run from the game, follow the comment at the
top of each file): `find_energy_writers.bat` → `count_energy_functions.bat` → `find_shot_caller.bat`;
`laser_pan.bat` (is the laser sound panned per cannon?), `haptics_tests.bat` (left / right output paths).
Addresses are absolute: the game's main module always loads at `0x140000000`.

## Files

`start.bat` play · `demo.bat` feel without the game · `scan.bat` signature check · `probe.bat` hooked
objects and values · `apply-dsx-profile.bat` write the DSX profile (DSX closed).
