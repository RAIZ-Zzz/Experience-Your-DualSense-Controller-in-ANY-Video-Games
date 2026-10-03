# Tasks: Iron Blight

Status: Phase 0 done (single-player, Unity IL2CPP, no anti-cheat); design chosen
Next: user checks the game accepts DSX's Xbox 360 pad (RT fires); demo feel test

## Todo
- [ ] Gamepad: does the game take DSX's virtual Xbox 360 pad, or only Steam Input → keyboard/mouse?
- [ ] Back up saves before the first hooked launch
- [ ] Demo feel test (`demo.bat`)
- [ ] Core: scan/hook inside a named module (`GameAssembly.dll`), on main
- [ ] Method addresses from global-metadata v39 (dumper that supports v39)
- [ ] active hook
- [ ] health hook
- [ ] shot hook
- [ ] current weapon → per-weapon trigger profile
- [ ] empty / jam → resistance off
- [ ] feel tuned with the player

## Done
- [x] Evidence: build version + SHA-256 (MODLOG.md)
- [x] Phase 0: audit, research, design choice
