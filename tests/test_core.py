"""Core tests. Run from the repo root:  python -m unittest discover tests"""
import io
import json
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from dualsense import autostart
from dualsense.bridge import run
from dualsense.dsx import Mode, Trigger, TriggerEffect, build_packet
from dualsense.effects import Effects, GameState
from dualsense.player import PlayerPicker
from dualsense.profile import merge

# Reference tuning (the Squadrons values; every game config has the same sections).
CFG = tomllib.loads((Path(__file__).parent.parent / "tests/config.toml").read_text(encoding="utf-8"))
FLYING = dict(attached=True, in_flight=True)


class BackgroundBridge(unittest.TestCase):
    """autostart keeps the bridge running all the time: without the game it must leave DSX alone."""

    class FakeDSX:
        addr = ("127.0.0.1", 0)

        def __init__(self):
            self.log = []

        def send(self, right, rgb=None):
            self.log.append("send")

        def reset(self):
            self.log.append("reset")

    def run_states(self, states, stop=None):
        it = iter(states)

        class Reader:
            def read(self):
                try:
                    return next(it)
                except StopIteration:
                    raise KeyboardInterrupt           # run() treats it as Ctrl+C

            def close(self):
                pass

        dsx = self.FakeDSX()
        with mock.patch("dualsense.bridge.time.sleep"), redirect_stdout(io.StringIO()):
            run(Reader(), dsx, CFG, *[stop] if stop else [])
        return dsx.log

    def test_sends_nothing_until_the_game_runs(self):
        log = self.run_states([GameState()] * 5 + [GameState(**FLYING)] + [GameState()] * 5)
        self.assertEqual(log, ["send", "reset", "reset"])     # play, game closed, exit

    def test_stop_file_ends_the_loop(self):
        with tempfile.TemporaryDirectory() as d:
            stop = Path(d) / "stop"
            stop.touch()
            self.assertEqual(self.run_states([GameState(**FLYING)] * 5, stop), ["reset"])

    def test_one_bridge_per_game(self):
        first = autostart.claim("_test_game")
        try:
            self.assertIsNone(autostart.claim("_test_game"))
            self.assertTrue(autostart.running("_test_game"))
        finally:
            first.close()
        self.assertFalse(autostart.running("_test_game"))


class DSXPacket(unittest.TestCase):
    def test_trigger_update_layout(self):
        pkt = json.loads(build_packet(0, {Trigger.RIGHT: TriggerEffect.auto_gun(2, 6, 18)}))
        self.assertEqual(pkt, {"instructions": [{"type": 1, "parameters": [0, 2, 17, 2, 6, 18]}]})

    def test_params_are_clamped(self):
        self.assertEqual(TriggerEffect.resistance(12, 99).params, (9, 8))


class TriggerEffects(unittest.TestCase):
    def frames(self, energy, shots, dt=1 / 60):
        """RT effect per frame; shots[i] = shots the game reported in frame i."""
        fx = Effects(CFG)
        return [fx.update(GameState(**FLYING, energy=energy, shots=n), i * dt) for i, n in enumerate(shots)]

    def test_menus_release_trigger(self):
        self.assertEqual(Effects(CFG).update(GameState(attached=True, in_flight=False), 0.0).mode, Mode.NORMAL)

    def pulses(self, shots, dt=1 / 200):
        """Number of separate vibration pulses for per-frame shot counts."""
        rt = self.frames(1.0, shots, dt)
        on = [e.mode == Mode.AUTOMATIC_GUN for e in rt]
        return sum(1 for a, b in zip([False] + on, on) if b and not a)

    def test_every_shot_is_one_pulse(self):
        f = CFG["fire"]
        pulse = TriggerEffect.auto_gun(0, f["pulse_strength"], f["pulse_frequency"])
        for e in (1.0, 0.0):                                              # 0.0: the game still fires single shots
            rt = self.frames(e, [0, 1] + [0] * 11)
            self.assertEqual(rt[1], pulse)
            self.assertEqual(rt[-1], TriggerEffect.resistance(f["base_start"], f["base_force"]))

    def test_held_fire_stays_one_pulse_per_shot(self):
        held = ([1] + [0] * 29) * 10                                      # 200 Hz frames, a shot every 0.15 s
        self.assertEqual(self.pulses(held), 10)
        fast = ([1] + [0] * 9) * 10                                       # even a 20 shots/s ship
        self.assertEqual(self.pulses(fast), 10)

    def test_resistance_same_at_any_energy(self):
        efs = {Effects(CFG).update(GameState(**FLYING, energy=e), 0.0) for e in (1.0, 0.5, 0.1, 0.0)}
        self.assertEqual(len(efs), 1)

    def test_no_shot_no_vibration(self):
        self.assertTrue(all(e.mode != Mode.AUTOMATIC_GUN for e in self.frames(0.5, [0] * 10)))

    def test_weapon_profile_overrides_fire(self):
        cfg = CFG | {"weapons": {"shotgun": {"pulse_strength": 3, "base_force": 5}}}
        fx = Effects(cfg)
        self.assertEqual(fx.update(GameState(**FLYING, weapon="shotgun"), 0.0).params[1], 5)
        self.assertEqual(fx.update(GameState(**FLYING, weapon="shotgun", shots=1), 1.0).params[1], 3)
        self.assertEqual(Effects(cfg).update(GameState(**FLYING, weapon="pistol"), 0.0),   # no profile: [fire]
                         Effects(CFG).update(GameState(**FLYING), 0.0))

    def test_rumble_one_kick_per_shot_off_without_config(self):
        cfg = CFG | {"fire": CFG["fire"] | {"rumble_right": 0.8, "rumble_seconds": 0.1}}
        fx = Effects(cfg)
        level = []
        for i, n in enumerate(([1] + [0] * 39) * 3):                     # 200 Hz, a shot every 0.2 s
            s = GameState(**FLYING, shots=n)
            fx.update(s, i / 200)
            level.append(fx.rumble(s, i / 200))
        kicks = sum(1 for a, b in zip([(0.0, 0.0)] + level, level) if any(b) and not any(a))
        self.assertEqual((kicks, max(level)), (3, (0.0, 0.8)))            # right motor only
        self.assertEqual(level[39], (0.0, 0.0))                           # quiet between shots
        fx = Effects(CFG)                                                 # no rumble keys (Squadrons)
        fx.update(GameState(**FLYING, shots=1), 1.0)
        self.assertEqual(fx.rumble(GameState(**FLYING), 1.0), (0.0, 0.0))

    def test_bump_rumbles_without_touching_the_trigger(self):
        cfg = CFG | {"bumps": {"kick": {"rumble_left": 0.7, "rumble_right": 0.7, "rumble_seconds": 0.15}}}
        fx = Effects(cfg)
        rt = fx.update(GameState(**FLYING, bumps=("kick",)), 1.0)
        self.assertEqual(rt, Effects(CFG).update(GameState(**FLYING), 1.0))       # same resistance, no pulse
        self.assertEqual(fx.rumble(GameState(**FLYING), 1.1), (0.7, 0.7))
        self.assertEqual(fx.rumble(GameState(**FLYING), 1.2), (0.0, 0.0))
        Effects(CFG).update(GameState(**FLYING, bumps=("unknown",)), 1.0)          # not configured: ignored

    def test_slack_drops_resistance_after_the_last_pulse(self):
        fx = Effects(CFG)
        self.assertEqual(fx.update(GameState(**FLYING, shots=1, slack=True), 1.0).mode, Mode.AUTOMATIC_GUN)
        self.assertEqual(fx.update(GameState(**FLYING, slack=True), 2.0).mode, Mode.NORMAL)


class Lightbar(unittest.TestCase):
    def rgb(self, hull, now=10.0):
        return Effects(CFG).lightbar(GameState(**FLYING, hull=hull), now)

    def test_damage_slides_and_flash_fades(self):
        fx = Effects(CFG)
        seq = []
        for i, h in enumerate([1.0] + [0.4] * 120):                   # big hit at frame 1, then 2 s
            s = GameState(**FLYING, hull=h)
            fx.update(s, i / 60)
            seq.append(fx.lightbar(s, i / 60))
        self.assertEqual((seq[1][0], seq[1][2]), (255, 0)); self.assertLess(seq[1][1], 10)   # hit snaps to red
        greens = [g for _, g, _ in seq[1:]]
        self.assertEqual(greens, sorted(greens))                       # then one smooth movement, no bounce
        self.assertAlmostEqual(seq[-1][1], self.rgb(0.4)[1], delta=2)  # ends on the new hull colour

    def test_green_yellow_red(self):
        self.assertEqual(self.rgb(1.0), (0, 255, 0))
        self.assertEqual(self.rgb(0.6), (255, 255, 0))           # halfway between full and red_at
        self.assertEqual(self.rgb(CFG["lightbar"]["red_at"]), (255, 0, 0))

    def test_critical_pulses_and_unknown_leaves_profile(self):
        levels = {self.rgb(0.1, t / 10)[0] for t in range(10)}
        self.assertGreater(len(levels), 3)
        self.assertIsNone(self.rgb(None))
        self.assertIsNone(Effects(CFG).lightbar(GameState(attached=True, hull=0.5), 0.0))   # menu

    def test_rgb_packet(self):
        pkt = json.loads(build_packet(0, {}, (1, 2, 3)))
        self.assertEqual(pkt, {"instructions": [{"type": 2, "parameters": [0, 1, 2, 3]}]})


class PlayerPick(unittest.TestCase):
    def test_player_is_the_ship_firing_while_rt_is_held(self):
        ps = PlayerPicker()
        self.assertEqual(ps.update([7, 3], True)[1] >= 1, True)            # first shot: trust RT
        for ai in (3, 5, 9, 3, 11):                                         # player 7 fires every poll, AI varies
            ps.update([7, ai], True)
        self.assertEqual(ps.update([3], False), (7, 0))                     # AI shot while RT released: no pulse
        self.assertEqual(ps.update([7], False), (7, 1))                     # trailing player shot still counts

    def test_new_mission_takes_over(self):
        ps = PlayerPicker(window=5)
        for _ in range(5):
            ps.update([1], True)
        for _ in range(5):
            ps.update([2], True)
        self.assertEqual(ps.update([], False)[0], 2)


class ProfileMerge(unittest.TestCase):
    def test_override_and_typo_guard(self):
        base = {"controller_motion": {"motion_mode": "NONE"}, "name": "x"}
        self.assertEqual(merge(base, {"controller_motion": {"motion_mode": "M"}})["controller_motion"]["motion_mode"], "M")
        with self.assertRaises(KeyError):
            merge(base, {"controller_motion": {"motoin_mode": "M"}})

    def test_nested_section_keeps_its_other_keys(self):
        base = {"controller_haptics": {"audio": {"source": "None", "gain": 3}, "x": 1}}
        out = merge(base, {"controller_haptics": {"audio": {"source": "SystemAudio"}}})
        self.assertEqual(out["controller_haptics"], {"audio": {"source": "SystemAudio", "gain": 3}, "x": 1})
        with self.assertRaises(KeyError):
            merge(base, {"controller_haptics": {"audio": {"sorce": "SystemAudio"}}})


if __name__ == "__main__":
    unittest.main()
