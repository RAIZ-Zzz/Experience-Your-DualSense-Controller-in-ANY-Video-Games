"""Single-player track: process memory and hook tests (they patch code in this test process only)."""
import ctypes
import os
import unittest

from dualsense.hook import PROLOGUE, InstalledSpy, Spy, build_cave
from dualsense.memory import Process, anti_cheat_running


class Memory(unittest.TestCase):
    def test_read_and_scan_own_process(self):
        buf = ctypes.create_string_buffer(b"\x11\x22\xDE\xAD\xBE\xEF\x33" + bytes(64))
        addr = ctypes.addressof(buf)
        p = Process(os.getpid())
        try:
            self.assertEqual(p.read(addr, 3), b"\x11\x22\xDE")
            self.assertIn(addr + 2, p.scan("DE ?? BE EF", addr, 16))
            self.assertTrue(p.alive())
        finally:
            p.close()

    def test_anti_cheat_guard(self):
        self.assertTrue(anti_cheat_running([(1, "easyanticheat.exe")]))
        self.assertFalse(anti_cheat_running([(1, "explorer.exe")]))


class Hook(unittest.TestCase):
    def test_spy_records_register_in_own_process(self):
        """Hook a tiny function in this process and call it: the cave must record rbx and keep behaviour."""
        k32 = ctypes.windll.kernel32
        k32.VirtualAlloc.restype = ctypes.c_void_p
        k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]
        f = k32.VirtualAlloc(None, 0x1000, 0x3000, 0x40)
        # push rbx; mov rbx,rcx; [site: mov rax,rbx; 5x nop]; pop rbx; ret   -> returns its argument
        code = bytes.fromhex("53 4889CB" "4889D8 9090909090" "5B C3")
        ctypes.memmove(f, code, len(code))
        fn = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64)(f)
        p = Process(os.getpid(), write=True)
        try:
            spy = InstalledSpy.install(p, Spy("t", "53 48 89 CB 48 89 D8 90 90 90 90 90 5B C3", 4, 8, "rbx"), f, 0x100)
            self.assertEqual([fn(0x1234), fn(0x1234), fn(0x5678)], [0x1234, 0x1234, 0x5678])
            self.assertEqual(spy.calls(), 3)
            self.assertEqual(spy.recent(), {0x1234: 2, 0x5678: 1})
            again = InstalledSpy.install(p, spy.spy, f, 0x100)              # re-attach to an already patched site
            self.assertEqual((again.cave, again.original), (spy.cave, spy.original))
            spy.remove()
            self.assertEqual(p.read(f, len(code)), code)
        finally:
            p.close()

    def test_cave_layout(self):
        self.assertEqual(len(build_cave(0x10000, 0x20000, bytes(6), "rcx")), PROLOGUE + 6 + 5)


if __name__ == "__main__":
    unittest.main()
