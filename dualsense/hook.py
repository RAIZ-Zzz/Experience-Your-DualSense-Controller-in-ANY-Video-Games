"""Register spy: patch one game instruction so it records the object pointer it works on.

The game keeps the player ship at a different address every mission, but the code that updates
energy / health is fixed and has the object in a register (rbx / rcx). External reads cannot see
registers, so we redirect that instruction to a small "cave" that copies the register into a
64-entry ring buffer, runs the original instruction(s), and jumps back.

Cave layout (one page, allocated within +-2 GB so plain rel32 jumps work):
    +0x000  magic  b"SQDSXHK1"
    +0x008  u32    call counter
    +0x010  u64[64] ring of recent register values (slot counter & 63 = newest)
    +0x210  code
"""
import struct
from collections import Counter
from dataclasses import dataclass

from .memory import pattern_to_regex

MAGIC = b"SQDSXHK1"
COUNTER, RING, CODE = 0x8, 0x10, 0x210
PROLOGUE = 0x20                      # cave code before the stolen bytes
RING_SIZE = 64
REGS = {"rcx": 1, "rbx": 3}          # registers we may record (not rax/rdx: the cave uses them)


def rel32(src_next, dst):
    d = dst - src_next
    if not -2**31 <= d < 2**31:
        raise ValueError("jump target out of rel32 range")
    return struct.pack("<i", d)


def build_cave(cave, site, stolen, reg):
    """Machine code at cave+CODE: record `reg` into the ring, run `stolen`, jump to site+len(stolen).
    `stolen` must not contain rip-relative operands (they would break when moved)."""
    x = cave + CODE
    code = bytearray(b"\x50\x52")                                         # push rax; push rdx
    code += b"\x8B\x05" + rel32(x + len(code) + 6, cave + COUNTER)        # mov eax,[counter]
    code += b"\xFF\xC0"                                                   # inc eax
    code += b"\x89\x05" + rel32(x + len(code) + 6, cave + COUNTER)        # mov [counter],eax
    code += b"\x83\xE0" + bytes([RING_SIZE - 1])                          # and eax,63
    code += b"\x48\x8D\x15" + rel32(x + len(code) + 7, cave + RING)       # lea rdx,[ring]
    code += b"\x48\x89" + bytes([0x04 | REGS[reg] << 3, 0xC2])            # mov [rdx+rax*8],reg
    code += b"\x5A\x58"                                                   # pop rdx; pop rax
    code += stolen                                                        # flags come from here on
    code += b"\xE9" + rel32(x + len(code) + 5, site + len(stolen))        # jmp back
    return bytes(code)


def patch_bytes(site, cave, n):
    """What goes at the hook site: jmp cave code, NOP-padded to the stolen length."""
    return b"\xE9" + rel32(site + 5, cave + CODE) + b"\x90" * (n - 5)


@dataclass(frozen=True)
class Spy:
    name: str
    pattern: str        # AOB of the original code
    offset: int         # hook site = match + offset
    stolen: int         # bytes moved into the cave (whole instructions, >= 5)
    reg: str

    def patched_pattern(self):
        """The same AOB after we patched it (to re-attach after the bridge was killed)."""
        toks = self.pattern.split()
        toks[self.offset:self.offset + self.stolen] = ["E9", "??", "??", "??", "??"] + ["90"] * (self.stolen - 5)
        return " ".join(toks)


class GameNotReady(RuntimeError):
    """Game memory unreadable or code not there (game starting, closing, or a different version)."""


def _read(proc, addr, n):
    data = proc.read(addr, n)
    if data is None:
        raise GameNotReady(f"cannot read game memory at {addr:#x}")
    return data


class InstalledSpy:
    def __init__(self, proc, spy, site, cave, original):
        self.proc, self.spy, self.site, self.cave, self.original = proc, spy, site, cave, original

    @classmethod
    def install(cls, proc, spy, start=None, size=None):
        """Patch the site (searched in the main module by default), or re-attach if already patched."""
        found = proc.scan(spy.patched_pattern(), start, size)
        if len(found) == 1:                                   # already patched by an earlier run
            site = found[0] + spy.offset
            cave = site + 5 + struct.unpack("<i", _read(proc, site + 1, 4))[0] - CODE
            if _read(proc, cave, len(MAGIC)) != MAGIC:
                raise RuntimeError(f"{spy.name}: site is patched by something else")
            original = _read(proc, cave + CODE + PROLOGUE, spy.stolen)
            return cls(proc, spy, site, cave, original)
        found = proc.scan(spy.pattern, start, size)
        if len(found) != 1:
            raise GameNotReady(f"{spy.name}: expected 1 match of the code signature, found {len(found)}")
        site = found[0] + spy.offset
        original = _read(proc, site, spy.stolen)
        cave = proc.alloc_near(site)
        proc.write(cave, MAGIC + bytes(CODE - len(MAGIC)) + build_cave(cave, site, original, spy.reg))
        proc.write(site, patch_bytes(site, cave, spy.stolen))
        return cls(proc, spy, site, cave, original)

    def remove(self):
        """Restore the original code. The cave stays allocated: a game thread may still be inside it."""
        self.proc.write(self.site, self.original)

    def calls(self):
        return struct.unpack("<I", _read(self.proc, self.cave + COUNTER, 4))[0]

    def since(self, prev_calls):
        """(calls now, register values recorded since `prev_calls`; at most the last 64)."""
        c = self.calls()
        ring = struct.unpack(f"<{RING_SIZE}Q", _read(self.proc, self.cave + RING, 8 * RING_SIZE))
        return c, [ring[i % RING_SIZE] for i in range(max(prev_calls, c - RING_SIZE) + 1, c + 1)]   # call k -> slot k & 63

    def recent(self):
        """Counter of pointer -> how often it is in the ring (ring = the last 64 calls)."""
        return Counter(self.since(0)[1])
