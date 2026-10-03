"""Every Iron Blight state the controller can meet (dualsense/states.py): dimensions, impossible combinations,
the snapshots each state gives the reader, and the design rules every output must follow.

    python -m games.iron_blight --states     simulate all, write states.json, print outputs grouped + rule breaks
"""
from pathlib import Path

from dualsense import states as S

from .reader import IronBlightReader

JSON = Path(__file__).with_name("states.json")

DIMS = {
    "play": ["playing", "paused", "dead", "menu"],          # menu = no player loaded (main menu, loading)
    "hand": ["gun", "holstering", "none"],                  # none = holstered (GunHandler.instance is null)
    "weapon": ["pistol", "revolver", "smg", "assaultRifle", "rifle", "shotgun", "melee"],
    "ammo": ["loaded", "empty"],                            # after this frame's event; melee: durability left
    "jammed": [False, True],                                # after this frame's event (a shot can jam the gun)
    "action": ["none", "reloading", "checking"],            # reloading also = clearing a jam
    "event": ["none", "shot", "kick", "melee_swing", "melee_hit", "hurt"],   # what happens in this frame
    "health": ["full", "low"],                              # low = 20 %, below the lightbar's critical 25 %
}

MELEE_ONLY = ("melee_swing", "melee_hit")
NEEDS_WEAPON = ("shot",) + MELEE_ONLY
IMPOSSIBLE = [
    # not playing: nothing in the game matters, one state each
    lambda s: s["play"] != "playing" and (s["hand"], s["weapon"], s["ammo"], s["jammed"], s["action"], s["event"],
                                          s["health"]) != ("gun", "pistol", "loaded", False, "none", "none", "full"),
    # holstered: no weapon fields exist (shown as the first value)
    lambda s: s["hand"] == "none" and (s["weapon"], s["ammo"], s["jammed"], s["action"]) != ("pistol", "loaded",
                                                                                            False, "none"),
    lambda s: s["hand"] != "gun" and s["event"] in NEEDS_WEAPON,          # no attack while holstered / holstering
    lambda s: s["hand"] == "holstering" and s["action"] != "none",
    # melee weapons: no magazine, no jam, no reload, no shots
    lambda s: s["weapon"] == "melee" and (s["ammo"], s["jammed"], s["action"]) != ("loaded", False, "none"),
    lambda s: s["weapon"] == "melee" and s["event"] == "shot",
    lambda s: s["weapon"] != "melee" and s["event"] in MELEE_ONLY,
    lambda s: s["event"] == "shot" and s["action"] != "none",            # no shot while reloading / checking
    lambda s: s["event"] == "hurt" and s["health"] == "full",            # a hit leaves less than full health
]


def frames(st):
    """The reader's snapshots for a state: [before this frame's event, after it]."""
    if st["play"] == "menu":
        return [None, None]
    health = {"full": 100.0, "low": 20.0}[st["health"]]
    base = {"health": health, "base_health": 100.0, "dead": st["play"] == "dead", "paused": st["play"] == "paused",
            "kicking": False, "kick_land": False, "kicks_left": 3, "gun": None}
    if st["hand"] != "none":
        melee = st["weapon"] == "melee"
        base |= {"gun": 0x1000, "selected": st["hand"] == "gun", "reloading": st["action"] == "reloading",
                 "checking": st["action"] == "checking", "shot_count": 5, "melee_attacking": False,
                 "melee_land": False, "ammo": 10 if melee else 8 if st["ammo"] == "loaded" else 0,
                 "weapon": st["weapon"], "jammed": st["jammed"], "melee": melee}
    before, after = dict(base), dict(base)
    event = st["event"]
    if event == "shot":
        before |= {"ammo": after["ammo"] + 1, "jammed": False, "shot_count": 4}
    elif event == "kick":                                                 # the blow lands (wind-up before)
        before["kicking"] = after["kicking"] = after["kick_land"] = True
    elif event == "melee_swing":
        before["melee_attacking"] = after["melee_attacking"] = after["melee_land"] = True
    elif event == "melee_hit":
        before["ammo"] = after["ammo"] + 1                                # durability drops on a hit
    elif event == "hurt":
        before["health"] = health + 30
    return [before, after]


class Replay(IronBlightReader):
    def __init__(self):
        super().__init__([], clock=lambda: 0.0)
        self.proc = object()                                              # "game running"


def run(st, cfg):
    return S.simulate(Replay(), cfg, frames(st))


def playing(s):
    return s["play"] == "playing"


def can_fire(s):
    return playing(s) and s["hand"] == "gun" and s["weapon"] != "melee" and s["ammo"] == "loaded" and not s["jammed"]


# The design the user chose, as rules every simulated output must follow.
INVARIANTS = [
    ("RT resistance only with a loaded, unjammed gun in hand (pulse instead on the shot frame)",
     lambda s, o: o["rt"].startswith("RESISTANCE") == (can_fire(s) and s["event"] != "shot")),
    ("RT pulse exactly on a shot",
     lambda s, o: o["rt"].startswith("AUTOMATIC_GUN") == (playing(s) and s["event"] == "shot")),
    ("RT never anything else than plain, resistance or the shot pulse",
     lambda s, o: o["rt"].split()[0] in ("NORMAL", "RESISTANCE", "AUTOMATIC_GUN")),
    ("one shot counted per shot, none for melee / kick / anything else",
     lambda s, o: o["shots"] == (1 if playing(s) and s["event"] == "shot" else 0)),
    ("grip: shot and melee swing = right motor only, kick = both, nothing else rumbles",
     lambda s, o: (o["rumble"][0] == 0 and o["rumble"][1] > 0) if playing(s) and s["event"] in ("shot", "melee_swing")
     else (min(o["rumble"]) > 0) if playing(s) and s["event"] == "kick" else o["rumble"] == [0, 0]),
    ("lightbar only while playing (menus / pause / death keep the DSX profile colour)",
     lambda s, o: (o["lightbar"] is not None) == playing(s)),
    ("a hit snaps the lightbar to red",
     lambda s, o: not (playing(s) and s["event"] == "hurt") or (o["lightbar"][0] > 200 and o["lightbar"][1] < 40)),
]


def all_rows(cfg):
    return S.table(S.expand(DIMS, IMPOSSIBLE), lambda st: run(st, cfg))
