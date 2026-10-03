"""Iron Blight -> DualSense. Options: --demo, --watch, --states (python -m games.iron_blight -h)."""
import tempfile
import time
from pathlib import Path

from dualsense.bridge import cli

from .reader import IronBlightReader

LOG = Path(tempfile.gettempdir()) / "iron_blight_watch.log"     # outside the repo and the game folder


def add_watch(ap):
    ap.add_argument("--watch", action="store_true",
                    help="print the game values read (read-only) whenever they change; nothing sent to DSX")
    ap.add_argument("--states", action="store_true",
                    help="simulate every game state, write states.json, print outputs grouped and rule breaks")

    def handle(args, cfg):
        if args.states:
            from dualsense import states as S
            from .states import INVARIANTS, JSON, all_rows
            rows = all_rows(cfg)
            S.save(JSON, rows)
            print(S.summary(rows))
            bad = S.violations(rows, INVARIANTS)
            print(f"\n{len(bad)} rule breaks" + "".join(f"\n  {st}\n    breaks: {rule}" for st, rule in bad[:40]))
            print(f"\nwrote {JSON}")
            return True
        if not args.watch:
            return False
        reader, last = IronBlightReader(cfg["game"]["process_names"], time.monotonic), "start"
        log = open(LOG, "a", encoding="utf-8")                # same lines as the window, for whoever debugs
        print(f"also writing to {LOG}")
        try:
            while True:
                try:
                    s = reader.snapshot(time.monotonic()) or "game not running, or no player loaded (menu)"
                except Exception as e:                    # game starting / closing: show it, keep watching
                    s = f"not ready: {e}"
                    reader.close()
                    time.sleep(2)
                if s != last:
                    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] {s}"
                    print(line)
                    log.write(line + "\n")
                    log.flush()
                    last = s
                time.sleep(0.005)
        except KeyboardInterrupt:
            return True

    return handle


if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"),
        lambda cfg, clock: IronBlightReader(cfg["game"]["process_names"], clock), add_watch)
