r"""Evidence record for a game build: size, SHA-256 and timestamp of each exe, to paste into the game's
README. Hooks are tied to one build; the hash says which. (Idea: the reverse-engineering skill of
gmh5225/awesome-game-security - record artifact hashes and versions with every finding.)

    python tools/evidence.py "C:\Games\Game\game.exe" [more.exe ...]
"""
import hashlib
import os
import sys
import time

for path in sys.argv[1:]:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    st = os.stat(path)
    print(f"| `{os.path.basename(path)}` | {st.st_size} | {time.strftime('%Y-%m-%d', time.localtime(st.st_mtime))} | `{h.hexdigest()}` |")
