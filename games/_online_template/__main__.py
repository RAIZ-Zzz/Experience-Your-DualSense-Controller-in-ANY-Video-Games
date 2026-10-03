"""<Game name> (online, telemetry) -> DualSense. Options: --demo (python -m games._online_template -h)."""
from pathlib import Path

from dualsense.bridge import cli

from .reader import TemplateTelemetry

if __name__ == "__main__":
    cli(Path(__file__).with_name("config.toml"), lambda cfg, clock: TemplateTelemetry(cfg["telemetry"]["port"], clock))
