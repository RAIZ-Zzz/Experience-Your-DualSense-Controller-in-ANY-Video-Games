"""Star Wars: Squadrons -> DualSense. Options: --demo, --scan, --probe (python -m games.star_wars_squadrons -h)."""
from pathlib import Path

from dualsense.bridge import cli
from dualsense.hooktools import add_options

from .reader import FIELDS, SIGNATURES, SPIES, SquadronsReader

if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"),
        lambda cfg, clock: SquadronsReader(cfg["game"]["process_names"], clock),
        add_options(SIGNATURES, SPIES, FIELDS))
