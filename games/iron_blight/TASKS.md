# Tasks: Iron Blight

Status: read-only reader written (no hooks), tested on fakes only
Next: user plays to the first gun with watch.bat open; check the values it prints

## Todo
- [ ] Gamepad: does the game take DSX's virtual Xbox 360 pad, or only Steam Input → keyboard/mouse?
- [ ] Back up saves before the first bridge run
- [ ] Demo feel test (`demo.bat`)
- [ ] watch.bat in the real game: classes found, scan time, health / ammo / jam / gunType / pause values
- [ ] ammoCount drops 1 per shot, not on reload or mag check (shotgun too)
- [ ] feel tuned with the player, per weapon actually picked up

## Done
- [x] Evidence: build version + SHA-256 (MODLOG.md)
- [x] Phase 0: audit, research, design choice
- [x] Route: read-only polling via core dualsense/il2cpp.py (no hooks, no dumper)
- [x] Reader: health, pause, death, shots from ammo, weapon type, empty/jam slack; per-weapon config
