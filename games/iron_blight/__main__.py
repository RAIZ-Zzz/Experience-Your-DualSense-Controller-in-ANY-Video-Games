"""<Game name> -> DualSense. Options: --demo, --scan, --probe (python -m games._template -h)."""
from pathlib import Path

from dualsense.bridge import cli
from dualsense.hooktools import add_options

from .reader import FIELDS, SIGNATURES, SPIES, TemplateReader

if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"),
        lambda cfg, clock: TemplateReader(cfg["game"]["process_names"], clock),
        add_options(SIGNATURES, SPIES, FIELDS))
