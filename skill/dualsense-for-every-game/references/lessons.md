# Lessons from the first game (Star Wars: Squadrons)

Each item: what happened, why, what to do next time.

## Environment

- **BSOD 0xD1 about 30 s after starting DSX.** Two minidumps, same fault: `steamxbox.sys +0x1b852`, Valve's
  "Xbox Extended Feature Support Driver", installed as a lower filter on the *whole* HID class, so it
  sees every DualSense and virtual-pad report. It read past a buffer when DSX created a virtual pad over
  Bluetooth. Fix: Steam → Settings → Controller → uninstall that driver, reboot. Proof: the exact
  scenario that crashed within 30 s ran cleanly afterwards.
- Minidumps in `C:\Windows\Minidump` need an admin shell to copy. A user's PowerShell prompt at
  `C:\Users\<name>` is not elevated; `Start-Process powershell -Verb RunAs ...` raises it.
- DSX writes its JSON files on exit, so edit them only while it is closed. Its UI edits land in the live
  profile, and a regenerate from `base_profile + toml` drops them unless the toml carries them.
- When the user "turns something off", check the live profile afterwards: one session showed a mix of
  half-applied changes.

## Finding state

- The FearLess CT table's AOBs still matched the newer build (1 match each), which saved hours.
- The energy-tick hook saw exactly one object in a training mission (only the player has an energy
  component there), so "most common object = player" seemed right. In a bigger mission it saw several
  ships at 330 calls/s, picked an AI ship, and the trigger feedback silently died. Fixed by `PlayerPicker`.
- Energy-drop shot detection worked (1 shot = 3.0 / 182) but needed a per-weapon threshold. The real
  per-shot function made the threshold unnecessary and also covered the single shots the game still
  fires at "empty" (20 of them in one recording).
- 112 writers of `+0x2E0` existed; the 8 near the known tick formed 5 tiny functions; one counting run
  identified the right one. Count first, read code second.
- The per-shot function had no direct callers (vtable). A return-address spy found its single caller.
- Use a different cave magic for experimental spies than the bridge's, or the bridge may re-attach to
  a foreign cave and misread its layout.
- A probe that runs at the same time as the user's bridge must not remove hooks it did not install.

## Bugs the tests caught before the user saw them

- Ring buffer read from slot 0 while the cave writes slot `counter & 63` after incrementing (off by one).
  Caught by executing the patched code in the test process.
- Hit flash fading and hull easing as two animations: red, then a bounce back toward green, then orange.
  Merged into one hue animation.
- First pulse of a burst (no previous gap known) swallowing the second shot; then a "push the next pulse
  later" fix that drifted until pulses merged at 20 shots/s. Final rule: cut a running pulse, rest 20 ms.
- Importing a test script without a `__main__` guard played the whole test sequence.

## Feel (what the user said, in order)

1. Fixed rattle while firing: "no interaction with the shots". → event-driven.
2. Resistance kick per shot: "no feedback" while the trigger is held. → vibration pulse.
3. Wall at empty energy, then "lighter as it drains", then "same at every energy, smaller". → constant 1.
4. Machine-gun vibration for held fire: "is it the same speed as the game?" No: it was free-running.
   → one pulse per real shot, length adapted to the gap.
5. Gyro to right stick: low sensitivity, then "the game has no gyro support, no recentering, remove it".

## Haptics experiments

- XInput rumble sent to DSX's virtual pad: left-only and right-only are distinguishable, but right is
  negligible next to left at any ratio. That is DSX's legacy-rumble mapping, not hardware (teardowns
  show identical actuators).
- Squadrons' laser sound alternates left / right per shot (81 % side flips over 60 shots) at only about
  ±0.1 pan.
- `tone_test` produced no vibration, but DSX had exited before the test and the loopback level was
  −26 dB. Not a conclusive result: rerun with DSX running and Windows volume at 100 %.
