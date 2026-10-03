# Tasks: Iron Blight

Status: read-only reader verified in game with the pistol (ammo, jam, reload, mag check, pause)
Next: start.bat feel test with the pistol; see a hit in watch.bat

## Todo
- [ ] Gamepad: does the game take DSX's virtual Xbox 360 pad, or only Steam Input → keyboard/mouse?
- [ ] Back up saves before the first bridge run
- [ ] Demo feel test (`demo.bat`)
- [ ] watch.bat: health drop on a hit
- [ ] ammoCount drops 1 per shot with the shotgun too (pistol verified)
- [ ] feel tuned with the player, per weapon actually picked up

## Done
- [x] Evidence: build version + SHA-256 (MODLOG.md)
- [x] Phase 0: audit, research, design choice
- [x] Route: read-only polling via core dualsense/il2cpp.py (no hooks, no dumper)
- [x] Reader: health, pause, death, shots from ammo, weapon type, empty/jam slack; per-weapon config
- [x] watch.bat in the real game: classes found; pistol ammo/jam/reload/mag check/pause as designed
