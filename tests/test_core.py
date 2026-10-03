"""Core tests. Run from the repo root:  python -m unittest discover tests"""
import ctypes
import json
import os
import tomllib
import unittest
from pathlib import Path

from dualsense.dsx import Mode, Trigger, TriggerEffect, build_packet
from dualsense.effects import Effects, GameState
from dualsense.hook import PROLOGUE, GameNotReady, InstalledSpy, Spy, build_cave
from dualsense.memory import Process, anti_cheat_running
from dualsense.player import PlayerPicker
from dualsense.profile import merge

# Reference tuning: the Squadrons config (any game config has the same sections).
CFG = tomllib.loads((Path(__file__).parent.parent / "games/squadrons/config.toml").read_text(encoding="utf-8"))
FLYING = dict(attached=True, in_flight=True)


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


class Memory(unittest.TestCase):
    def test_read_and_scan_own_process(self):
        buf = ctypes.create_string_buffer(b"\x11\x22\xDE\xAD\xBE\xEF\x33" + bytes(64))
        addr = ctypes.addressof(buf)
        p = Process(os.getpid())
        try:
            self.assertEqual(p.read(addr, 3), b"\x11\x22\xDE")
            self.assertIn(addr + 2, p.scan("DE ?? BE EF", addr, 16))
            self.assertTrue(p.alive())
        finally:
            p.close()

    def test_anti_cheat_guard(self):
        self.assertTrue(anti_cheat_running([(1, "easyanticheat.exe")]))
        self.assertFalse(anti_cheat_running([(1, "explorer.exe")]))


class Hook(unittest.TestCase):
    def test_spy_records_register_in_own_process(self):
        """Hook a tiny function in this process and call it: the cave must record rbx and keep behaviour."""
        k32 = ctypes.windll.kernel32
        k32.VirtualAlloc.restype = ctypes.c_void_p
        k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
        f = k32.VirtualAlloc(None, 0x1000, 0x3000, 0x40)
        # push rbx; mov rbx,rcx; [site: mov rax,rbx; 5x nop]; pop rbx; ret   -> returns its argument
        code = bytes.fromhex("53 4889CB" "4889D8 9090909090" "5B C3")
        ctypes.memmove(f, code, len(code))
        fn = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64)(f)
        p = Process(os.getpid(), write=True)
        try:
            spy = InstalledSpy.install(p, Spy("t", "53 48 89 CB 48 89 D8 90 90 90 90 90 5B C3", 4, 8, "rbx"), f, 0x100)
            self.assertEqual([fn(0x1234), fn(0x1234), fn(0x5678)], [0x1234, 0x1234, 0x5678])
            self.assertEqual(spy.calls(), 3)
            self.assertEqual(spy.recent(), {0x1234: 2, 0x5678: 1})
            again = InstalledSpy.install(p, spy.spy, f, 0x100)              # re-attach to an already patched site
            self.assertEqual((again.cave, again.original), (spy.cave, spy.original))
            spy.remove()
            self.assertEqual(p.read(f, len(code)), code)
        finally:
            p.close()

    def test_cave_layout(self):
        self.assertEqual(len(build_cave(0x10000, 0x20000, bytes(6), "rcx")), PROLOGUE + 6 + 5)


if __name__ == "__main__":
    unittest.main()
