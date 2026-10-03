"""Generic reader: game state from a few hooked instructions. Games subclass HookReader (see games/_template)."""
import time

from .effects import GameState
from .hook import GameNotReady, InstalledSpy
from .memory import Process
from .player import PlayerPicker, right_trigger


class HookReader:
    """Game state from hooked game code (see hook.py). A game subclasses this and sets:
        SPIES   {name: Spy}                 hooks to install
        FIELDS  {name: (cur_off, max_off)}  float pair read from a hooked object -> fraction
        ACTIVE  spy name whose code runs every frame while playing (silent in menus / pause)
        HEALTH  spy name whose object holds the player's health (None = no lightbar)
        SHOT    spy name of the "player fired one shot" code (None = no per-shot trigger)
        ENERGY  FIELDS name read from the shot object for weapon energy / ammo (None = unknown)
    Shot code usually runs for every character / ship, AI included, so the player's object is picked
    by PlayerPicker: the one whose shots happen while RT is held."""

    SPIES, FIELDS = {}, {}
    ACTIVE = HEALTH = SHOT = ENERGY = None

    IDLE_SECONDS = 0.5      # hooked code silent this long -> menu / pause / cutscene
    RT_HELD = 30            # XInput RT value (0-255) that counts as firing
    RETRY_SECONDS = 2.0     # game starting / closing: wait this long before attaching again

    def __init__(self, process_names, clock, trigger=right_trigger):
        self.process_names = process_names
        self.clock = clock
        self.trigger = trigger
        self.proc = None
        self.spies = {}
        self.seen = {}      # spy name -> (last call count, time it last changed)
        self.shot_calls = 0
        self.player = PlayerPicker()
        self.retry_at = 0.0
        self.last_error = None

    def _attach(self):
        todo = [name for name, spy in self.SPIES.items() if "TODO" in spy.pattern]
        if todo:
            raise GameNotReady(f"signature not filled in yet: {', '.join(todo)}")
        self.proc = Process.find(self.process_names, write=True)
        if self.proc is not None:
            self.spies = {name: InstalledSpy.install(self.proc, spy) for name, spy in self.SPIES.items()}
            self.seen = {}
            self.shot_calls = self.spies[self.SHOT].calls() if self.SHOT else 0
            self.player = PlayerPicker()

    def _active(self, name, now):
        calls = self.spies[name].calls()
        last_calls, changed = self.seen.get(name, (None, now))
        if calls != last_calls:
            changed = now
        self.seen[name] = (calls, changed)
        return bool(calls) and now - changed <= self.IDLE_SECONDS

    def _fraction(self, ptr, field):
        cur_off, max_off = self.FIELDS[field]
        cur, mx = self.proc.read_float(ptr + cur_off), self.proc.read_float(ptr + max_off)
        if cur is None or not mx or mx <= 0 or not -0.01 <= cur <= mx * 1.01:
            return None
        return max(0.0, min(1.0, cur / mx))

    def read(self):
        """GameState; never raises for a game that is starting, closing or not running (retries later)."""
        now = self.clock()
        if now < self.retry_at:
            return GameState()
        try:
            return self._read(now)
        except (GameNotReady, OSError) as e:          # OSError: WinError from write / allocate
            if self.proc:
                self.proc.close()
            self.proc, self.spies = None, {}
            self.retry_at = now + self.RETRY_SECONDS
            if str(e) != self.last_error:
                print(f"[{time.strftime('%H:%M:%S')}] game not ready ({e}); retrying")
                self.last_error = str(e)
            return GameState()

    def _read(self, now):
        if self.proc and not self.proc.alive():
            self.proc.close()
            self.proc, self.spies = None, {}
        if self.proc is None:
            self._attach()
            if self.proc is None:
                return GameState()
            self.last_error = None
        playing = self._active(self.ACTIVE, now)
        hull = None
        if self.HEALTH and self._active(self.HEALTH, now):
            hull = self._fraction(self.spies[self.HEALTH].recent().most_common(1)[0][0], self.HEALTH)
        player, shots = None, 0
        if self.SHOT:
            self.shot_calls, objs = self.spies[self.SHOT].since(self.shot_calls)
            player, shots = self.player.update(objs, self.trigger() >= self.RT_HELD)
        energy = self._fraction(player, self.ENERGY) if playing and player and self.ENERGY else None
        return GameState(attached=True, in_flight=playing or hull is not None,
                         energy=energy, hull=hull, shots=shots if playing else 0)

    def close(self):
        """Put the game code back (if the game is still running)."""
        if self.proc and self.proc.alive():
            for spy in self.spies.values():
                try:
                    spy.remove()
                except OSError:          # game closing underneath us: nothing left to restore
                    pass
        self.spies = {}
