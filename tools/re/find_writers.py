"""Every instruction in the game's main module that writes a dword to [reg+OFFSET] (movss / vmovss / mov).

    python tools/re/find_writers.py game.exe 2E0 > writers.txt

Step 1 of "who changes this value": most hits are unrelated classes that share the offset; the real ones
sit next to code you already know. Disassemble those (common.dis), then hook the candidate functions'
entries with count_calls.py."""
import struct
import sys
import time

from common import attach, cs, synced

exe, off = sys.argv[1], int(sys.argv[2], 16)
d = struct.pack("<I", off).hex(" ").upper()
p = attach(exe)
pats = [f"F3 0F 11 ?? {d}", f"F3 ?? 0F 11 ?? {d}", f"C5 FA 11 ?? {d}", f"C4 ?? 7A 11 ?? {d}", f"89 ?? {d}", f"C7 ?? {d}"]
t = time.time()
found = []
for pat in pats:
    for a in p.scan(pat):
        if not synced(p, a):
            continue
        i = next(cs.disasm(p.read(a, 16), a), None)
        if i and f"+ {off:#x}]" in i.op_str and i.op_str.startswith("dword ptr ["):
            found.append((a, f"{i.mnemonic} {i.op_str}"))
for a, s in sorted(set(found)):
    print(f"{a:#x}  {s}")
print(len(found), "writers", f"{time.time() - t:.0f}s", file=sys.stderr)
