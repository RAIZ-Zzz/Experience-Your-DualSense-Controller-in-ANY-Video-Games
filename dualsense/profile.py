"""Generate a game's DSX controller profile from one of your DSX profiles + the game's dsx_profile.toml.

    python -m dualsense.profile games/<name>/dsx_profile.toml             write "<name>.dsx" next to your DSX profiles
    python -m dualsense.profile games/<name>/dsx_profile.toml --activate  also make it the DualSense's active profile

DSX must be closed (it rewrites its files on exit). Existing files are backed up as *.bak first.
"""
import argparse
import json
import shutil
import subprocess
import tomllib
from pathlib import Path



def merge(base, overrides):
    """Return base with overrides applied section by section, nested sections ([a.b]) key by key too;
    unknown keys are an error (typo guard)."""
    out = json.loads(json.dumps(base))
    for section, values in overrides.items():
        if not isinstance(values, dict):
            continue
        if section not in out:
            raise KeyError(f"DSX profile has no section '{section}'")
        _merge_into(out[section], values, section)
    return out


def _merge_into(target, values, path):
    for key, value in values.items():
        if key not in target:
            raise KeyError(f"DSX profile section '{path}' has no key '{key}'")
        if isinstance(value, dict) and isinstance(target[key], dict):
            _merge_into(target[key], value, f"{path}.{key}")
        else:
            target[key] = value


def backup_and_write(path, text):
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("overrides", help="the game's dsx_profile.toml")
    ap.add_argument("--activate", action="store_true")
    args = ap.parse_args()

    with open(args.overrides, "rb") as f:
        ov = tomllib.load(f)
    running = subprocess.run(["tasklist", "/FI", "IMAGENAME eq DSX.exe", "/NH"], capture_output=True, text=True).stdout
    if "dsx.exe" in running.lower():
        raise SystemExit("Close DSX first (tray icon -> Exit), then run this again.")

    cfg_dir = Path(ov["dsx_dir"]) / "DSX_Savefile" / "Configuration Files"
    profiles = cfg_dir / "Controller Profiles"
    base = json.loads((profiles / f"{ov['base_profile']}.dsx").read_text(encoding="utf-8-sig"))
    profile = merge(base, ov)
    profile["name"] = ov["name"]
    target = profiles / f"{ov['name']}.dsx"
    backup_and_write(target, json.dumps(profile, indent=2, ensure_ascii=False))
    print(f"Wrote {target}")

    if args.activate:
        devices_path = cfg_dir / "Devices Info" / "DevicesInfoList.json"
        devices = json.loads(devices_path.read_text(encoding="utf-8-sig"))
        for c in devices["controllers_list"]:
            if c["device_data"]["device_type"].startswith("DUALSENSE"):
                c["device_data"]["profile_name"] = c["device_data"]["profile_name_bluetooth"] = ov["name"]
                print(f"Activated for {c['device_data']['mac_address']}")
        backup_and_write(devices_path, json.dumps(devices, indent=2, ensure_ascii=False))
    print("Start DSX again to load it.")


if __name__ == "__main__":
    main()
