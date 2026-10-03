"""Online track: the guard that keeps game memory off-limits, and the telemetry reader."""
import re
import socket
import struct
import unittest
from pathlib import Path

from dualsense.effects import GameState
from dualsense.telemetry import UdpTelemetryReader

ROOT = Path(__file__).resolve().parent.parent

# APIs / modules that open, read, write or inject into another process (ONLINE_RULES.md 1, 2, 4).
FORBIDDEN = [
    "OpenProcess", "ReadProcessMemory", "WriteProcessMemory", "VirtualAllocEx", "VirtualProtectEx",
    "CreateRemoteThread", "NtReadVirtualMemory", "NtWriteVirtualMemory", "QueueUserAPC",
    "SetWindowsHookEx", "DebugActiveProcess", "MiniDumpWriteDump", "pymem", "frida",
    r"dualsense\.memory", r"dualsense\.hook", r"from \.memory", r"from \.hook",
]


class OnlineGuard(unittest.TestCase):
    def test_no_process_memory_or_injection_anywhere(self):
        pattern = re.compile("|".join(FORBIDDEN))
        hits = []
        for path in ROOT.rglob("*.py"):
            if path.resolve() == Path(__file__).resolve() or ".git" in path.parts:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
        self.assertEqual(hits, [], "online track must never touch game memory (ONLINE_RULES.md)")


class Telemetry(unittest.TestCase):
    class Fake(UdpTelemetryReader):
        """<float hull, uint32 shots_total> per packet."""
        prev = None

        def parse(self, data, state):
            hull, total = struct.unpack("<fI", data)
            shots = total - self.prev if self.prev is not None else 0
            self.prev = total
            return GameState(attached=True, in_flight=True, hull=hull, shots=shots)

    def test_packets_become_state_and_silence_means_not_running(self):
        t = [0.0]
        r = self.Fake(0, clock=lambda: t[0])          # port 0: the OS picks a free one
        out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.assertEqual(r.read(), GameState())   # nothing received yet
            addr = r.sock.getsockname()
            for hull, total in ((1.0, 10), (0.9, 12), (0.8, 13)):
                out.sendto(struct.pack("<fI", hull, total), addr)
            for _ in range(100):                      # localhost UDP: give the packets a moment
                s = r.read()
                if s.attached:
                    break
            self.assertAlmostEqual(s.hull, 0.8, places=5)
            self.assertEqual(s.shots, 3)              # 12-10 + 13-12, summed over the packets of this read
            t[0] = 5.0
            self.assertEqual(r.read(), GameState())   # game stopped sending
        finally:
            out.close()
            r.close()


if __name__ == "__main__":
    unittest.main()
