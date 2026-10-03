"""The loop every game shares: read game state -> effects -> DSX. Plus the demo reader and a small CLI,
so a game's __main__.py is a few lines.

    python -m games.<name>            run against the game (waits for it to start)
    python -m games.<name> --demo     simulated play, to feel the effects without the game
"""
import argparse
import time
import tomllib

from .dsx import DSX
from .effects import Effects, GameState


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


def run(reader, dsx, cfg):
    effects = Effects(cfg)
    period = 1 / cfg["loop"]["hz"]
    resend = cfg["dsx"]["resend_seconds"]
    last, last_sent, last_status = None, 0.0, None
    print(f"Sending to DSX at {dsx.addr[0]}:{dsx.addr[1]} - Ctrl+C to stop")
    try:
        while True:
            now = time.monotonic()
            state = reader.read()
            status = "playing" if state.in_flight else "game running" if state.attached else "waiting for game"
            if status != last_status:
                print(f"[{time.strftime('%H:%M:%S')}] {status}")
                last_status = status
            out = (effects.update(state, now), effects.lightbar(state, now))
            if last and last[1] is not None and out[1] is None:
                dsx.reset()                                  # leaving play: give the LED back to the profile
            if out != last or now - last_sent >= resend:     # resend keeps DSX in sync after profile switches
                dsx.send(*out)
                last, last_sent = out, now
            time.sleep(max(0.0, period - (time.monotonic() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        reader.close()
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
    handle = extra(ap) if extra else None
    args = ap.parse_args()
    cfg = load_config(args.config)
    if handle and handle(args, cfg):
        return
    reader = DemoReader(time.monotonic) if args.demo else make_reader(cfg, time.monotonic)
    run(reader, DSX(cfg["dsx"]["port"], cfg["dsx"]["controller"]), cfg)
