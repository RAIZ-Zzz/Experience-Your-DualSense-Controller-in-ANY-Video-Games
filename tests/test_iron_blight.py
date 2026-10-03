"""Iron Blight reader logic on scripted snapshots (no game needed); config parses with every weapon profile."""
import tomllib
import unittest
from pathlib import Path

from dualsense.dsx import Mode
from dualsense.effects import Effects
from games.iron_blight.reader import IronBlightReader

GUN, OTHER = 0x1000, 0x2000
CFG = tomllib.loads((Path(__file__).parent.parent / "games/iron_blight/config.toml").read_text(encoding="utf-8"))


def snap(ammo, gun=GUN, **kw):
    s = dict(health=80.0, base_health=100.0, dead=False, paused=False, gun=gun, ammo=ammo, weapon="pistol",
             jammed=False, melee=False, reloading=False, checking=False, shot_count=0)
    return s | kw


class Scripted(IronBlightReader):
    def __init__(self, snaps):
        super().__init__(["x.exe"], clock=lambda: 0.0)
        self.snaps = iter(snaps)
        self.proc = object()

    def snapshot(self, now):
        return next(self.snaps)


def states(*snaps):
    r = Scripted(snaps)
    return [r._read(0.0) for _ in snaps]


class Shots(unittest.TestCase):
    def test_each_round_fired_is_one_shot(self):
        self.assertEqual([s.shots for s in states(snap(8), snap(7), snap(7), snap(5))], [0, 1, 0, 2])

    def test_reload_and_mag_check_are_not_shots(self):
        seq = states(snap(3), snap(0, reloading=True), snap(8, reloading=True), snap(8), snap(1, checking=True))
        self.assertEqual([s.shots for s in seq], [0] * 5)

    def test_melee_durability_drop_is_not_a_shot(self):
        m = dict(melee=True, weapon="melee")
        self.assertEqual([s.shots for s in states(snap(10, **m), snap(9, **m))], [0, 0])

    def test_jammed_shot_kicks_then_nothing_until_cleared(self):
        # the in-game trace of 02:12:48-51: jam on the 3rd shot, clearing shows as reloading
        seq = states(snap(7), snap(6, jammed=True), snap(6, jammed=True, reloading=True),
                     snap(6, reloading=True), snap(6))
        self.assertEqual([s.shots for s in seq], [0, 1, 0, 0, 0])
        self.assertEqual([s.slack for s in seq], [False, True, True, False, False])

    def test_kick_rumbles_when_it_lands_not_when_pressed(self):
        # the in-game trace of 03:03:27: press, 0.42 s wind-up, land window, done
        seq = states(snap(4), snap(4, kicking=True), snap(4, kicking=True, kick_land=True), snap(4))
        self.assertEqual([s.bumps for s in seq], [(), (), ("kick",), ()])
        self.assertEqual(states(snap(8), snap(8, kick_land=True, paused=True))[1].bumps, ())

    def test_melee_rumbles_when_the_blow_can_land(self):
        m = dict(melee=True, weapon="melee")
        seq = states(snap(5, **m), snap(5, melee_attacking=True, **m),
                     snap(5, melee_attacking=True, melee_land=True, **m), snap(4, **m))
        self.assertEqual([s.bumps for s in seq], [(), (), ("melee",), ()])

    def test_switching_guns_resets_the_count(self):
        self.assertEqual([s.shots for s in states(snap(8), snap(2, gun=OTHER), snap(1, gun=OTHER))], [0, 0, 1])

    def test_paused_or_dead_is_not_playing(self):
        a, b = states(snap(8), snap(7, paused=True))
        self.assertTrue(a.in_flight)
        self.assertEqual((b.in_flight, b.shots), (False, 0))
        self.assertFalse(states(snap(8, dead=True))[0].in_flight)


class Trigger(unittest.TestCase):
    def test_empty_or_jammed_is_slack_melee_never(self):
        self.assertEqual([s.slack for s in states(snap(1), snap(0), snap(5, jammed=True))], [False, True, True])
        self.assertFalse(states(snap(0, melee=True, weapon="melee"))[0].slack)
        self.assertTrue(states(snap(None, gun=None, weapon=None))[0].slack)          # no gun: plain trigger
        # the in-game holster trace of 02:44:26: isSelected False while the holster animation plays
        self.assertEqual([s.slack for s in states(snap(8, selected=True), snap(8, selected=False))], [False, True])
        fx = Effects(CFG)
        self.assertEqual(fx.update(states(snap(0))[0], 5.0).mode, Mode.NORMAL)

    def test_health_fraction_and_weapon(self):
        s = states(snap(8, weapon="shotgun"))[0]
        self.assertEqual((s.hull, s.weapon), (0.8, "shotgun"))
        self.assertIsNone(states(snap(None, gun=None, weapon=None))[0].weapon)

    def test_every_weapon_profile_uses_known_keys(self):
        for name, profile in CFG["weapons"].items():
            self.assertLessEqual(set(profile), set(CFG["fire"]), name)


class EveryState(unittest.TestCase):
    """All enumerated states (games/iron_blight/states.py): design rules hold, and the outputs equal the
    reviewed states.json (regenerate with python -m games.iron_blight --states after a deliberate change)."""

    def test_design_rules_hold_in_every_state(self):
        from dualsense import states as S
        from games.iron_blight.states import INVARIANTS, all_rows
        self.assertEqual(S.violations(all_rows(CFG), INVARIANTS), [])

    def test_outputs_match_states_json(self):
        from dualsense import states as S
        from games.iron_blight.states import JSON, all_rows
        self.assertEqual(all_rows(CFG), S.load(JSON), "behaviour changed: review, then rerun --states")


if __name__ == "__main__":
    unittest.main()
