"""Who calls this function? Records the caller's return address ([rsp] at function entry).
Needed when the function is only reached through a vtable, so there are no direct call sites to search.

    python tools/re/retspy.py game.exe 0x1418849c0 8 60      (entry, bytes stolen, seconds)

Squadrons: the per-shot method had exactly one caller (0x1417b4c0b) - so no weapon can bypass it."""
import struct
import sys
import time
from collections import Counter

from common import attach, dis
from dualsense.hook import CODE, COUNTER, RING, RING_SIZE, patch_bytes, rel32

MAGIC = b"SQDSXRET"   # differs from hook.MAGIC so the bridge never mistakes this cave for its own


def build_ret_cave(cave, site, stolen, depth=0):
    """Record qword [rsp + 8*depth] as seen at the hooked instruction (depth 0 = return address at entry)."""
    x = cave + CODE
    c = bytearray(b"\x50\x52\x51")                                         # push rax, rdx, rcx
    c += b"\x48\x8B\x4C\x24" + bytes([0x18 + 8 * depth])                  # mov rcx,[rsp+0x18+8*depth]
    c += b"\x8B\x05" + rel32(x + len(c) + 6, cave + COUNTER)              # mov eax,[counter]
    c += b"\xFF\xC0"                                                      # inc eax
    c += b"\x89\x05" + rel32(x + len(c) + 6, cave + COUNTER)              # mov [counter],eax
    c += b"\x83\xE0" + bytes([RING_SIZE - 1])                             # and eax,63
    c += b"\x48\x8D\x15" + rel32(x + len(c) + 7, cave + RING)             # lea rdx,[ring]
    c += b"\x48\x89\x0C\xC2"                                              # mov [rdx+rax*8],rcx
    c += b"\x59\x5A\x58"                                                  # pop rcx, rdx, rax
    c += stolen
    c += b"\xE9" + rel32(x + len(c) + 5, site + len(stolen))              # jmp back
    return bytes(c)


class RetSpy:
    def __init__(self, p, site, n):
        self.p, self.site = p, site
        self.original = p.read(site, n)
        self.cave = p.alloc_near(site)
        p.write(self.cave, MAGIC + bytes(CODE - len(MAGIC)) + build_ret_cave(self.cave, site, self.original))
        p.write(site, patch_bytes(site, self.cave, n))

    def calls(self):
        return struct.unpack("<I", self.p.read(self.cave + COUNTER, 4))[0]

    def recent(self):
        c = self.calls()
        ring = struct.unpack(f"<{RING_SIZE}Q", self.p.read(self.cave + RING, 8 * RING_SIZE))
        return Counter(ring[i % RING_SIZE] for i in range(c - min(c, RING_SIZE) + 1, c + 1))

    def remove(self):
        self.p.write(self.site, self.original)


if __name__ == "__main__":
    exe, addr, n, secs = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3]), float(sys.argv[4])
    p = attach(exe, write=True)
    s = RetSpy(p, addr, n)
    seen = Counter()
    try:
        t0 = time.time()
        while time.time() - t0 < secs:
            seen.update(s.recent())
            time.sleep(0.05)
    finally:
        s.remove()
    print(f"{s.calls()} calls")
    for ra, _ in seen.most_common(5):
        print(f"===== returns to {ra:#x}")
        dis(p, ra - 0x40, 0x50, ra)
