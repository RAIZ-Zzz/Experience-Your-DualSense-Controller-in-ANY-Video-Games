# Tasks: Iron Blight

Status: working in game (pistol): RT pulse + right-grip kick per shot, slack trigger when it can't fire,
kick rumble at impact, health lightbar; 550 enumerated states pass the design rules
Next: feel-tune with the player (kick / melee timing, per-weapon strength)

## Todo
- [ ] Melee: a hit on an enemy (does ammoCount = durability drop?); air swings measured
- [ ] Feel: kick rumble now at canKickLand - confirm it lines up with the kick on screen
- [ ] Feel: RT pulse / grip strength per weapon (only the pistol felt so far)
- [ ] watch.bat: health drop on a hit (lightbar flash never seen in game)
- [ ] ammoCount drops 1 per shot with the shotgun too (pistol verified)
- [ ] Shots 8 and 9 were 11 ms apart on 2026-10-04 02:13:05: double tap or the game's last-round logic?
- [ ] DSX audio haptics: does it stay on after a DSX restart without applying the profile?
- [ ] First attach takes ~40 s (full memory scan); restrict the scan to private RW regions if it bothers
- [ ] README (Evidence, How the state was found, Measured) and release zip (Phase 5)

## Done
- [x] Evidence: build version + SHA-256 (MODLOG.md)
- [x] Phase 0: audit, research, design choice
- [x] Route: read-only polling via core dualsense/il2cpp.py (no hooks, no dumper)
- [x] Reader: health, pause, death, shots from ammo, weapon type, empty/jam slack; per-weapon config
- [x] watch.bat in the real game: classes found; pistol ammo/jam/reload/mag check/pause as designed
- [x] Grip rumble per shot (Xbox right motor via DSX), pistol light ... shotgun heaviest
- [x] Slack trigger: no gun, holstering, empty, jammed, reloading, mag check (all measured or enumerated)
- [x] Melee never counts as a shot; kick / melee grip rumble; kick at canKickLand (measured 0.42 s wind-up)
- [x] DSX profile: Xbox rumble -> haptics, audio haptics kept on, Trigger To Haptics off
- [x] states.py: 550 states enumerated, 7 design rules, states.json reviewed; old bugs proven caught
- [x] watch.bat also logs to %TEMP%\iron_blight_watch.log
