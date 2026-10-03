"""DSX (Paliverse, Steam v3.1+) UDP client.

Protocol: one JSON packet per datagram to 127.0.0.1:<port>
    {"instructions": [{"type": <InstructionType>, "parameters": [controller, trigger, mode, ...]}]}
Enum values come from DSX's shared protocol definitions (see UnityDSX_VR SharedInfo.cs).
DSX must have Settings -> Networking -> Incoming UDP enabled.
"""
import json
import os
import socket
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class Instruction(IntEnum):
    TRIGGER_UPDATE = 1
    RGB_UPDATE = 2
    PLAYER_LED = 3
    TRIGGER_THRESHOLD = 4
    MIC_LED = 5
    PLAYER_LED_NEW_REVISION = 6
    RESET_TO_USER_SETTINGS = 7


class Trigger(IntEnum):
    LEFT = 1
    RIGHT = 2


class Mode(IntEnum):
    NORMAL = 0
    GAMECUBE = 1
    VERY_SOFT = 2
    SOFT = 3
    HARD = 4
    VERY_HARD = 5
    HARDEST = 6
    RIGID = 7
    VIBRATE_TRIGGER = 8
    CHOPPY = 9
    MEDIUM = 10
    VIBRATE_TRIGGER_PULSE = 11
    CUSTOM_TRIGGER_VALUE = 12
    RESISTANCE = 13          # start 0-9, force 0-8
    BOW = 14
    GALLOPING = 15
    SEMI_AUTOMATIC_GUN = 16  # start 2-7, end 0-8, force 0-8
    AUTOMATIC_GUN = 17       # start 0-9, strength 0-8, frequency 0-255 (keep < 40)
    MACHINE = 18
    VIBRATE_TRIGGER_10HZ = 19
    OFF = 20
    FEEDBACK = 21
    WEAPON = 22
    VIBRATION = 23
    SLOPE_FEEDBACK = 24
    MULTIPLE_POSITION_FEEDBACK = 25
    MULTIPLE_POSITION_VIBRATION = 26


def _clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


@dataclass(frozen=True)
class TriggerEffect:
    mode: Mode
    params: tuple[int, ...] = ()

    @staticmethod
    def normal():
        return TriggerEffect(Mode.NORMAL)

    @staticmethod
    def resistance(start, force):
        return TriggerEffect(Mode.RESISTANCE, (_clamp(start, 0, 9), _clamp(force, 0, 8)))

    @staticmethod
    def semi_auto(start, end, force):
        return TriggerEffect(Mode.SEMI_AUTOMATIC_GUN, (_clamp(start, 2, 7), _clamp(end, 0, 8), _clamp(force, 0, 8)))

    @staticmethod
    def auto_gun(start, strength, frequency):
        return TriggerEffect(Mode.AUTOMATIC_GUN, (_clamp(start, 0, 9), _clamp(strength, 0, 8), _clamp(frequency, 0, 255)))


def default_port():
    """DSX writes its UDP port to %LOCALAPPDATA%\\DSX\\DSX_UDP_PortNumber.txt (v3.1 beta 1.37+)."""
    try:
        return int((Path(os.environ["LOCALAPPDATA"]) / "DSX" / "DSX_UDP_PortNumber.txt").read_text().strip())
    except (KeyError, OSError, ValueError):
        return 6969


def build_packet(controller, effects, rgb=None):
    """effects: {Trigger: TriggerEffect}, rgb: (r, g, b) lightbar or None. Returns the UTF-8 JSON datagram."""
    instructions = [
        {"type": Instruction.TRIGGER_UPDATE, "parameters": [controller, trig, eff.mode, *eff.params]}
        for trig, eff in effects.items()
    ]
    if rgb is not None:
        instructions.append({"type": Instruction.RGB_UPDATE, "parameters": [controller, *rgb]})
    return json.dumps({"instructions": instructions}).encode()


class DSX:
    def __init__(self, port=0, controller=0):
        self.addr = ("127.0.0.1", port or default_port())
        self.controller = controller
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, right, rgb=None):
        """RT effect and optional lightbar colour. LT is never touched (stays on the DSX profile)."""
        self.sock.sendto(build_packet(self.controller, {Trigger.RIGHT: right}, rgb), self.addr)

    def reset(self):
        """Hand the triggers and lightbar back to the user's DSX profile."""
        pkt = {"instructions": [{"type": Instruction.RESET_TO_USER_SETTINGS, "parameters": [self.controller]}]}
        self.sock.sendto(json.dumps(pkt).encode(), self.addr)
