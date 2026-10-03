"""Single-player track: CLI options for games read through hooks (--scan, --probe). Touches game memory."""
import time

from .hook import InstalledSpy
from .memory import Process


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


def add_options(signatures, spies, fields):
    """For bridge.cli(extra=...): adds --scan and --probe."""
    def extra(ap):
        ap.add_argument("--scan", action="store_true", help="check the code signatures inside the running game")
        ap.add_argument("--probe", action="store_true", help="hook the game and print the objects the hooked code touches")

        def handle(args, cfg):
            names = cfg["game"]["process_names"]
            if args.scan:
                proc = Process.find(names)
                if proc is None:
                    print("Game not running.")
                    return True
                for name, pattern in signatures.items():
                    if "TODO" in pattern:
                        print(f"{name}: not filled in yet")
                        continue
                    addrs = proc.scan(pattern)
                    print(f"{name}: {len(addrs)} match(es) {[hex(a) for a in addrs[:5]]}")
                proc.close()
                return True
            if args.probe:
                probe(names, spies, fields)
                return True
            return False
        return handle
    return extra
