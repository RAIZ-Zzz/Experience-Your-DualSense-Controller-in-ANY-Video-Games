"""Shared helpers for the reverse-engineering tools (dev only: pip install capstone; audio_pan also numpy soundcard).
Run the tools from the repo root, e.g.  python tools/re/find_writers.py game.exe 2E0"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import capstone  # noqa: E402

from dualsense.memory import Process  # noqa: E402

cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def attach(exe, write=False):
    p = Process.find([exe], write=write)
    if p is None:
        sys.exit(f"{exe} is not running")
    return p


def dis(proc, addr, size, mark=None):
    """Print a disassembly; `mark` gets an arrow."""
    for i in cs.disasm(proc.read(addr, size), addr):
        print(f"{'>>' if i.address == mark else '  '} {i.address:#x}  {i.bytes.hex():<24} {i.mnemonic} {i.op_str}")


def synced(proc, addr, back=96):
    """True if linear disassembly started at many points before `addr` lands exactly on it (not mid-instruction)."""
    hits = 0
    for b in range(back, back - 16, -1):
        code = proc.read(addr - b, b + 16)
        if code is None:
            return False
        for i in cs.disasm(code, addr - b):
            if i.address >= addr:
                hits += i.address == addr
                break
    return hits >= 12


def parse_hooks(args):
    """['0x1418849c0:8:rcx', ...] -> [(addr, stolen, reg)]"""
    out = []
    for a in args:
        addr, n, reg = a.split(":")
        out.append((int(addr, 16), int(n), reg))
    return out
