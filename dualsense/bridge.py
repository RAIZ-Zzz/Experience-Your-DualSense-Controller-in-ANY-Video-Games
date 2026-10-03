"""The loop every game shares: read game state -> effects -> DSX. Plus the demo reader, the hook probe
and a small CLI, so a game's __main__.py is a few lines (see games/_template/__main__.py).

    python -m games.<name>            run against the game (waits for it to start)
    python -m games.<name> --demo     simulated play, to feel the effects without the game
    python -m games.<name> --scan     check the game's code signatures inside the running game
    python -m games.<name> --probe    hook the game and print the objects the hooked code touches
"""
import argparse
import time
import tomllib

from .dsx import DSX
from .effects import Effects, GameState
from .hook import InstalledSpy
from .memory import Process


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


def probe(process_names, spies, fields):
    """Development aid: which objects pass through each hooked instruction, and their (current, max) floats."""
    proc = Process.find(process_names, write=True)
    if proc is None:
        print("Game not running.")
        return
    installed = [InstalledSpy.install(proc, s) for s in spies.values()]
    print("Hooked. Play, fire, take damage. Ctrl+C restores the game code.")
    try:
        while True:
            time.sleep(1)
            print(f"--- {time.strftime('%H:%M:%S')}")
            for spy in installed:
                print(f"{spy.spy.name}: {spy.calls()} calls")
                cur, mx = fields.get(spy.spy.name, (None, None))
                for ptr, n in spy.recent().most_common(8):
                    vals = f"{proc.read_float(ptr + cur)} / {proc.read_float(ptr + mx)}" if cur is not None else ""
                    print(f"  {ptr:#x} x{n:<2}  {vals}")
    except KeyboardInterrupt:
        pass
    finally:
        for spy in installed:
            spy.remove()
        print("Game code restored.")


def cli(config_path, make_reader, signatures, spies, fields):
    """Entry point for games/<name>/__main__.py. make_reader(process_names, clock) -> reader."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=config_path)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    names = cfg["game"]["process_names"]

    if args.scan:
        proc = Process.find(names)
        if proc is None:
            return print("Game not running.")
        for name, pattern in signatures.items():
            if "TODO" in pattern:
                print(f"{name}: not filled in yet")
                continue
            addrs = proc.scan(pattern)
            print(f"{name}: {len(addrs)} match(es) {[hex(a) for a in addrs[:5]]}")
        return proc.close()
    if args.probe:
        return probe(names, spies, fields)

    reader = DemoReader(time.monotonic) if args.demo else make_reader(names, time.monotonic)
    run(reader, DSX(cfg["dsx"]["port"], cfg["dsx"]["controller"]), cfg)
