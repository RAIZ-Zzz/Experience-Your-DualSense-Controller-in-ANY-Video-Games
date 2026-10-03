# Tasks: star-wars-squadrons

Status: playable - RT one pulse per shot (any ship), hull lightbar
Next: test DSX 3.2 "virtual DualSense with audio" as a silent wireless left/right haptics path

## Todo
- [ ] DSX 3.2 beta: does the virtual DualSense expose a 4-channel audio endpoint? (write to channels 3/4)
- [ ] Does Squadrons accept a virtual DualSense as input? If not, haptics stay on audio capture
- [ ] Hit flash strength proportional to damage (idea from RDR2 - DSX, see prior-art.md)
- [ ] Trigger: no vibration after RT is released (ForzaDSX click note)
- [ ] Optional: "rigid wall" recoil as an alternative shot feel (RDR2 - DSX)
- [ ] Per-weapon trigger profiles from the weapon data at [obj+0x388]
- [ ] Health hook still assumes one object; fix like the shot hook if a mission breaks it

## Done
- [x] EAC off for offline modes (PCGamingWiki launcher rename), restore via EA app Repair
- [x] BSOD root cause: steamxbox.sys (Steam Xbox extended feature driver), uninstalled
- [x] Hooks: energy tick, hull, per-shot method (260 shots = 260 calls)
- [x] Player picked by RT correlation (bigger missions run the shot code for many ships)
- [x] RT: one pulse per shot, length adapts to fire rate, 20 ms rest, light constant resistance
- [x] Lightbar: hue green -> yellow -> red, eased, hit snaps red, pulse below 25 %
- [x] Bridge survives the game starting / closing (GameNotReady + retry)
- [x] Gyro removed (game has no gyro support, no recentering)
- [x] Per-cannon left/right haptics: cancelled (Xbox-emulated rumble is always left-heavy)
