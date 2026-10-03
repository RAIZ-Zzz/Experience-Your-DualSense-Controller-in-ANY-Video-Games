"""Star Wars: Squadrons -> DualSense. See dualsense/bridge.py for the options (--demo, --scan, --probe)."""
from pathlib import Path

from dualsense.bridge import cli

from .reader import FIELDS, SIGNATURES, SPIES, SquadronsReader

if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"), SquadronsReader, SIGNATURES, SPIES, FIELDS)
