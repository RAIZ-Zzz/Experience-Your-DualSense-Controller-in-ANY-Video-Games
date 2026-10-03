"""<Game name> (PC, build <version>, offline) -> GameState.   Copy this folder to games/<name>/ and fill in.

How each hook is found: see skill/dualsense-for-every-game/SKILL.md (phase 3) and tools/re/.
Until a signature is filled in the reader just reports "game not ready" and retries - nothing breaks."""
from dualsense.hook import Spy
from dualsense.reader import HookReader

# AOBs of whole instructions inside the hooked code. Use "??" for bytes that change between builds.
SIGNATURES = {
    "active": "TODO",   # code that runs every frame while playing, silent in menus / pause
    "health": "TODO",   # code that reads the player's health; its register holds the health object
    "shot": "TODO",     # code that runs exactly once per shot fired (any shooter; the player is picked by RT)
}
SPIES = {
    # Spy(name, pattern, offset of the hooked instruction in the pattern, bytes stolen (whole instructions,
    #     >= 5, no rip-relative operands), register holding the object: "rbx" or "rcx")
    "active": Spy("active", SIGNATURES["active"], 0, 5, "rbx"),
    "health": Spy("health", SIGNATURES["health"], 0, 5, "rcx"),
    "shot": Spy("shot", SIGNATURES["shot"], 0, 5, "rcx"),
}
FIELDS = {
    "health": (0x0, 0x4),   # TODO (current, max) float offsets in the health object
    "ammo": (0x0, 0x4),     # TODO (current, max) float offsets in the shot object, or drop ENERGY below
}


class TemplateReader(HookReader):
    SPIES, FIELDS = SPIES, FIELDS
    ACTIVE = "active"
    HEALTH = "health"   # None if not found yet: no lightbar
    SHOT = "shot"       # None if not found yet: no per-shot trigger
    ENERGY = "ammo"     # None if unknown
