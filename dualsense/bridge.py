"""The loop every game shares: read game state -> effects -> DSX. Plus the demo reader and a small CLI,
so a game's __main__.py is a few lines.

    python -m games.<name>            run against the game (waits for it to start)
    python -m games.<name> --demo     simulated play, to feel the effects without the game
    python -m games.<name> --autostart on|off   run it in the background from Windows logon (autostart.py)
"""
import argparse
import sys
import time
import tomllib
from pathlib import Path

from . import autostart
from .dsx import DSX
from .effects import Effects, GameState
from .player import rumble


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def run(reader, dsx, cfg, stop=None):
    """stop: a Path; the loop ends cleanly once it exists (checked once a second; autostart's "off")."""
    effects = Effects(cfg)
    period = 1 / cfg["loop"]["hz"]
    resend = cfg["dsx"]["resend_seconds"]
    last, last_sent, last_status, last_rumble, checked = None, 0.0, None, (0.0, 0.0), 0.0
    print(f"Sending to DSX at {dsx.addr[0]}:{dsx.addr[1]} - Ctrl+C to stop")
    try:
        while True:
            now = time.monotonic()
            if stop and now - checked >= 1.0:
                if stop.exists():
                    break
                checked = now
            state = reader.read()
            status = "playing" if state.in_flight else "game running" if state.attached else "waiting for game"
            if status != last_status:
                print(f"[{time.strftime('%H:%M:%S')}] {status}")
                last_status = status
            out = (effects.update(state, now), effects.lightbar(state, now))
            if not state.attached:
                # game not running: send nothing, so a bridge left running in the background never fights
                # another game (or its own DSX profile) for the controller
                if last is not None:
                    dsx.reset()
                    last = None
            else:
                if last and last[1] is not None and out[1] is None:
                    dsx.reset()                              # leaving play: give the LED back to the profile
                if out != last or now - last_sent >= resend:  # resend keeps DSX in sync after profile switches
                    dsx.send(*out)
                    last, last_sent = out, now
            r = effects.rumble(state, now)
            if r != last_rumble:                             # only on change: a game's own rumble is left alone
                rumble(*r)
                last_rumble = r
            # waiting for the game: look once a second instead of spinning at loop.hz
            time.sleep(max(0.0, (period if state.attached else 1.0) - (time.monotonic() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        reader.close()
        if any(last_rumble):
            rumble(0.0, 0.0)
        dsx.reset()
        print("Game code restored, triggers handed back to DSX profile.")


class DemoReader:
    """Fake play for testing without the game: 3 s of held fire (8 shots/s), 2 s of single shots (2/s,
    like taps), 3 s of recharge, repeat; hull drops 5 % every 3 s."""

    def __init__(self, clock):
        self.clock = clock
        self.t0 = clock()
        self.fired = 0

    def read(self):
        t = self.clock() - self.t0
        phase = t % 8
        fired = int(phase * 8) if phase < 3 else 24 + int((phase - 3) * 2) if phase < 5 else 0   # shots this cycle
        energy = max(0.0, 1 - 0.035 * fired) if phase < 5 else min(1.0, (phase - 5) / 3)
        shots, self.fired = max(0, fired - self.fired), fired
        hull = 1.0 - (0.05 * int(t // 3)) % 1.0             # -5% every 3 s, wraps back to full
        return GameState(attached=True, in_flight=True, energy=energy, hull=hull, shots=shots)

    def close(self):
        pass


def cli(config_path, make_reader, extra=None):
    """Entry point for games/<name>/__main__.py. make_reader(cfg, clock) -> reader.
    extra(args, cfg) may add track-specific options (single-player branch: hooktools.add_options)."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=config_path)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--autostart", choices=["on", "off"],
                    help="on: run in the background from Windows logon, waiting for the game; off: stop and remove")
    handle = extra(ap) if extra else None
    args = ap.parse_args()
    game_dir = Path(config_path).resolve().parent
    game = game_dir.name
    if args.autostart:
        autostart.on(game, game_dir.parent.parent) if args.autostart == "on" else autostart.off(game)
        return
    cfg = load_config(args.config)
    if handle and handle(args, cfg):
        return
    dsx = DSX(cfg["dsx"]["port"], cfg["dsx"]["controller"])
    if args.demo:
        return run(DemoReader(time.monotonic), dsx, cfg)
    lock = autostart.claim(game)
    if lock is None:
        print("Already running (in the background if autostart is on). Stop it: --autostart off")
        return
    if sys.stdout is None:                                   # pythonw (autostart): no console, log to a file
        sys.stdout = sys.stderr = open(autostart.log_file(game), "w", encoding="utf-8", buffering=1)
    run(make_reader(cfg, time.monotonic), dsx, cfg, stop=autostart.stop_file(game))
