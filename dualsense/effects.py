"""Game state -> RT trigger effect and lightbar colour. Pure logic, no I/O. Works for any game whose
reader fills GameState; the feel is tuned in the game's config.toml ([fire], [hit], [lightbar])."""
import colorsys
import math
from dataclasses import dataclass

from .dsx import TriggerEffect

NORMAL = TriggerEffect.normal()


@dataclass
class GameState:
    attached: bool = False            # game process found
    in_flight: bool = False           # player is in control (False in menus / pause / cutscenes)
    energy: float | None = None       # weapon energy / ammo 0..1, None = unknown
    hull: float | None = None         # health 0..1, None = unknown
    shots: int = 0                    # shots the player fired since the previous read
    weapon: str | None = None         # key into config [weapons.<name>] (overrides [fire]), None = [fire]
    slack: bool = False               # weapon can't fire (empty, jammed): no resistance between shots


class Effects:
    """Holds what effects need across frames: previous hull, last shot and hit times, shown hue."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.prev_hull = None
        self.shot_at = self.hit_at = -math.inf
        self.pulse = 0.0
        self.pulse_start = -math.inf
        self.shown_hue = None
        self.flashed_at = -math.inf
        self.last_now = None

    def update(self, state, now):
        """-> RT effect, driven by the shots the game fires (state.shots, from its per-shot code).
        Every shot = exactly one vibration pulse. The pulse lasts pulse_seconds, but never more than
        pulse_share of the time since the previous shot, so held fire stays one distinct knock per shot at
        any fire rate instead of blurring into a buzz. Between shots: a light, constant resistance, none while
        state.slack (the last shot's pulse still plays out). A weapon's [weapons.<name>] keys override [fire]."""
        if not (state.attached and state.in_flight):
            self.prev_hull = None
            return NORMAL
        f = self.cfg["fire"] | self.cfg.get("weapons", {}).get(state.weapon, {})
        if state.shots:
            end = self.pulse_start + self.pulse
            # keep pulses apart: a shot mid-pulse cuts it and starts after a break; a shot just after one
            # waits out the rest of the break. Delay is at most pulse_break, and never accumulates.
            self.pulse_start = now + f["pulse_break"] if self.pulse_start <= now < end else max(now, end + f["pulse_break"])
            self.pulse = min(f["pulse_seconds"], (now - self.shot_at) * f["pulse_share"])
            self.shot_at = now

        h = state.hull
        if h is not None and self.prev_hull is not None and self.prev_hull - h >= self.cfg["hit"]["min_drop"]:
            self.hit_at = now
        self.prev_hull = h

        if self.pulse_start <= now < self.pulse_start + self.pulse:
            return TriggerEffect.auto_gun(0, f["pulse_strength"], f["pulse_frequency"])
        if state.slack or f["base_force"] <= 0:
            return NORMAL
        return TriggerEffect.resistance(f["base_start"], f["base_force"])

    def lightbar(self, state, now):
        """Lightbar (r, g, b) from hull, or None to leave the DSX profile's LED alone.
        Hue goes green -> yellow -> red with the hull (an RGB fade would pass through dim olive) and eases
        instead of jumping; a hit snaps it to red and it eases back to the hull's colour in one movement.
        Below `critical` the light pulses faster as the hull drops, so it reads without colour vision."""
        lb = self.cfg["lightbar"]
        dt = 0.0 if self.last_now is None else now - self.last_now
        self.last_now = now
        if not (lb["enabled"] and state.attached and state.in_flight) or state.hull is None:
            self.shown_hue = None
            return None
        target = max(0.0, min(1.0, (state.hull - lb["red_at"]) / (1 - lb["red_at"]))) / 3   # 1/3 green, 0 red
        if self.shown_hue is None:
            self.shown_hue = target
        if self.hit_at > self.flashed_at:
            self.shown_hue, self.flashed_at = 0.0, self.hit_at
        self.shown_hue += (target - self.shown_hue) * (1 - math.exp(-dt / lb["smooth_seconds"]))

        level = 1.0
        if state.hull < lb["critical"]:
            slow, fast = lb["pulse_hz"]
            hz = slow + (fast - slow) * (1 - state.hull / lb["critical"])
            level = lb["pulse_min"] + (1 - lb["pulse_min"]) * (0.5 + 0.5 * math.cos(2 * math.pi * hz * now))
        return tuple(round(c * 255 * level) for c in colorsys.hsv_to_rgb(self.shown_hue, 1.0, 1.0))
