"""Star Wars: Squadrons (PC, EA app build 1.0.10.39591, offline / EAC disabled) -> GameState."""
from dualsense.hook import Spy
from dualsense.reader import HookReader

# Code signatures. The exe is EA-DRM encrypted on disk, so these only exist in memory while the game runs.
#   energy: per-frame tick of the weapon-energy component, object in rbx (from the FearLess CT table).
#   health: hull health read, object in rcx (from the same CT table).
#   shot:   the weapon's "pay for one shot" virtual method: energy -= [[obj+388]+8] * [obj+490]. Found by
#           hooking every function that changes energy: 260 player shots = 260 calls, also for shots at
#           "empty". Single caller 0x1417b4c0b. Runs for every ship, AI included -> PlayerPicker.
SIGNATURES = {
    "energy": "00 F3 0F 10 83 D0 03 00 00 0F 2F 83 E0 02 00 00",
    "health": "0F 28 F0 48 8B 01 FF 90 10 01 00 00 F3",
    "shot": "F3 0F 10 89 E0 02 00 00 48 8B 81 88 03 00 00 F3 0F 10 40 08 F3 0F 59 81 90 04 00 00 F3 0F 5C C8",
}
SPIES = {
    "energy": Spy("energy", SIGNATURES["energy"], 1, 8, "rbx"),   # movss xmm0,[rbx+3D0]
    "health": Spy("health", SIGNATURES["health"], 0, 6, "rcx"),   # movaps xmm6,xmm0; mov rax,[rcx]
    "shot": Spy("shot", SIGNATURES["shot"], 0, 8, "rcx"),         # movss xmm1,[rcx+2E0] (function entry)
}
FIELDS = {"energy": (0x2E0, 0x3D0), "health": (0x20, 0x24), "shot": (0x2E0, 0x3D0)}   # (current, max) floats


class SquadronsReader(HookReader):
    SPIES, FIELDS = SPIES, FIELDS
    ACTIVE = "energy"     # energy tick runs every frame in flight, stops in menus / pause
    HEALTH = "health"
    SHOT = "shot"
    ENERGY = "shot"       # the shot object is the weapon-energy object: +0x2E0 / +0x3D0
