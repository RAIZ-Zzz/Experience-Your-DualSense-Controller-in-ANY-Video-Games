"""Run a game's bridge in the background from Windows logon: no window, it waits for the game, one per game.

    python -m games.<name> --autostart on    shortcut in the Startup folder, and start it now
    python -m games.<name> --autostart off   stop it cleanly (hooks restored, LED/RT back to the DSX profile),
                                             remove the shortcut

While the game is not running the bridge sends nothing to DSX (bridge.run), so it can stay running.
Its output goes to %TEMP%\\dualsense_<name>.log.
"""
import msvcrt
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

STARTUP = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
TMP = Path(tempfile.gettempdir())


def shortcut(game):
    return STARTUP / f"DualSense {game}.lnk"


def stop_file(game):
    return TMP / f"dualsense_{game}.stop"


def log_file(game):
    return TMP / f"dualsense_{game}.log"


def claim(game):
    """Lock held for the life of this game's bridge (keep the returned file open); None if one already runs."""
    f = open(TMP / f"dualsense_{game}.lock", "a+")
    f.seek(0)
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        f.close()
        return None
    stop_file(game).unlink(missing_ok=True)       # a stale "off" request must not stop this new run
    return f


def running(game):
    f = claim(game)
    if f:
        f.close()
    return f is None


def on(game, root):
    """root: the folder that holds dualsense/ and games/."""
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        raise SystemExit(f"pythonw.exe not found next to {sys.executable}")
    q = lambda p: str(p).replace("'", "''")         # PowerShell single-quoted string
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{q(shortcut(game))}'); "
                    f"$s.TargetPath = '{q(pythonw)}'; $s.Arguments = '-m games.{game}'; "
                    f"$s.WorkingDirectory = '{q(root)}'; $s.Description = 'DualSense effects for {game}'; $s.Save()"],
                   check=True)
    if not running(game):
        subprocess.Popen([str(pythonw), "-m", f"games.{game}"], cwd=root, creationflags=subprocess.DETACHED_PROCESS)
    print(f"On: starts with Windows ({shortcut(game)}) and runs now in the background, waiting for the game.\n"
          f"Log: {log_file(game)}")


def off(game, timeout=10.0):
    shortcut(game).unlink(missing_ok=True)
    if running(game):
        stop_file(game).touch()
        end = time.monotonic() + timeout
        while running(game) and time.monotonic() < end:
            time.sleep(0.2)
        if running(game):
            raise SystemExit(f"still running after {timeout:.0f} s; see {log_file(game)}")
    stop_file(game).unlink(missing_ok=True)
    print("Off: stopped, and it no longer starts with Windows.")
