"""Iron Blight -> DualSense. Options: --demo, --watch (python -m games.iron_blight -h)."""
import time
from pathlib import Path

from dualsense.bridge import cli

from .reader import IronBlightReader


def add_watch(ap):
    ap.add_argument("--watch", action="store_true",
                    help="print the game values read (read-only) whenever they change; nothing sent to DSX")

    def handle(args, cfg):
        if not args.watch:
            return False
        reader, last = IronBlightReader(cfg["game"]["process_names"], time.monotonic), "start"
        try:
            while True:
                try:
                    s = reader.snapshot(time.monotonic()) or "game not running, or no player loaded (menu)"
                except Exception as e:                    # game starting / closing: show it, keep watching
                    s = f"not ready: {e}"
                    reader.close()
                    time.sleep(2)
                if s != last:
                    print(f"[{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}] {s}")
                    last = s
                time.sleep(0.005)
        except KeyboardInterrupt:
            return True

    return handle


if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"),
        lambda cfg, clock: IronBlightReader(cfg["game"]["process_names"], clock), add_watch)
