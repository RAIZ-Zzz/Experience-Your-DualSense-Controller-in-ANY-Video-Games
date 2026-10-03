# Star Wars: Squadrons

EA app build **1.0.10.39591**, PC. Single-player only: Story and Practice.

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

## Files

`start.bat` play · `demo.bat` feel without the game · `scan.bat` signature check · `probe.bat` hooked
objects and values · `apply-dsx-profile.bat` write the DSX profile (DSX closed).
