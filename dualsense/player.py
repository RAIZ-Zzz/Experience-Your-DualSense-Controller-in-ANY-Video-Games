"""Which in-game object is the player's: the one whose code runs while the player presses the button.

Shared game code (fire a shot, pay energy, ...) usually runs for every ship / character, AI included.
Correlating it with the real button press picks the player without knowing anything about the game."""
import ctypes
from collections import Counter, deque


class _XInputGamepad(ctypes.Structure):
    _fields_ = [("buttons", ctypes.c_ushort), ("lt", ctypes.c_ubyte), ("rt", ctypes.c_ubyte),
                ("thumbs", ctypes.c_short * 4)]


class _XInputState(ctypes.Structure):
    _fields_ = [("packet", ctypes.c_uint), ("pad", _XInputGamepad)]


def triggers():
    """(LT, RT) 0-255, highest over all XInput pads. With DSX emulating an Xbox pad, this is what the game reads."""
    try:
        x = ctypes.WinDLL("xinput1_4")
    except OSError:
        return 0, 0
    lt = rt = 0
    s = _XInputState()
    for i in range(4):
        if x.XInputGetState(i, ctypes.byref(s)) == 0:
            lt, rt = max(lt, s.pad.lt), max(rt, s.pad.rt)
    return lt, rt


def right_trigger():
    return triggers()[1]


class PlayerPicker:
    """Votes from the last `window` polls in which the button was held and the hooked code ran;
    the object with most votes is the player's. A new level (new objects) takes over within a few events."""

    def __init__(self, window=20):
        self.polls = deque(maxlen=window)

    def update(self, objs, held):
        """objs: objects the hooked code ran for since the last poll. -> (player object or None, player events)."""
        if objs and held:
            self.polls.append(set(objs))
        votes = Counter(o for poll in self.polls for o in poll)
        player = votes.most_common(1)[0][0] if votes else None
        if player is None:
            return None, 1 if objs and held else 0       # very first event: trust the button
        return player, sum(o == player for o in objs)
