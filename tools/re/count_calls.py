"""Hook function entries and count every call (and the object in the register) for N seconds.
Compare with what you did in game, e.g. to find the one function that runs exactly once per shot.

    python tools/re/count_calls.py game.exe 120 0x1418849c0:8:rcx 0x1418847d0:8:rcx ...
        hook = entry address : bytes stolen (whole instructions >= 5, no rip-relative) : register with the object

Prints per function: total calls, distinct objects, top objects. Restores the code at the end.
Squadrons: of 5 energy-changing functions only one ran, 260 times for 260 shots by the player."""
import sys
import time
from collections import Counter

from common import attach, parse_hooks
from dualsense.hook import InstalledSpy, Spy

exe, secs, hooks = sys.argv[1], float(sys.argv[2]), parse_hooks(sys.argv[3:])
p = attach(exe, write=True)
spies = {}
for addr, n, reg in hooks:
    pat = p.read(addr, 16).hex(" ").upper()
    spies[hex(addr)] = InstalledSpy.install(p, Spy(hex(addr), pat, 0, n, reg), addr, 16)
print(f"hooked {len(spies)} functions for {secs:.0f} s - go do the thing in game", flush=True)
per_obj = {k: Counter() for k in spies}
last = {k: s.calls() for k, s in spies.items()}
t0 = time.perf_counter()
try:
    while time.perf_counter() - t0 < secs:
        for k, s in spies.items():
            last[k], objs = s.since(last[k])
            per_obj[k].update(objs)
        time.sleep(0.002)
finally:
    for s in spies.values():
        s.remove()
for k, c in per_obj.items():
    print(f"{k}: {sum(c.values())} calls, {len(c)} objects  " + ", ".join(f"{o:#x} x{n}" for o, n in c.most_common(5)))
