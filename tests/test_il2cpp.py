"""il2cpp.py against a fake game process: synthetic v39 metadata + the runtime structs that point into it."""
import struct
import unittest

from dualsense.hook import GameNotReady
from dualsense.il2cpp import Il2Cpp, Metadata

STRINGS = b"\0Player\0instance\0health\0"        # index 0 = "" (global namespace)
NAME, F_INSTANCE, F_HEALTH = 1, 8, 17


def metadata():
    head = 8 + 31 * 12
    s_off, f_off = head, head + len(STRINGS)
    t_off = f_off + 20
    sec = [(0, 0, 0)] * 31
    sec[2], sec[11], sec[19] = (s_off, len(STRINGS), 3), (f_off, 20, 2), (t_off, 76, 1)
    typedef = bytearray(76)
    struct.pack_into("<ii", typedef, 0, NAME, 0)
    struct.pack_into("<i", typedef, 20, 0)        # fieldStart
    struct.pack_into("<H", typedef, 56, 2)        # field_count
    fields = struct.pack("<iHi", F_INSTANCE, 0, 0) + struct.pack("<iHi", F_HEALTH, 0, 0)
    return (struct.pack("<Ii", 0xFAB11BAF, 39) + b"".join(struct.pack("<iii", *s) for s in sec)
            + STRINGS + fields + bytes(typedef))


class FakeProcess:
    def __init__(self):
        self.mem = {}                             # base -> bytearray

    def put(self, addr, data):
        self.mem[addr] = bytearray(data)

    def regions(self, start, end):
        for base in sorted(self.mem):
            yield base, base + len(self.mem[base])

    def read(self, addr, size):
        for base, b in self.mem.items():
            if base <= addr and addr + size <= base + len(b):
                return bytes(b[addr - base:addr - base + size])
        return None

    def read_ptr(self, addr):
        b = self.read(addr, 8)
        return None if b is None else struct.unpack("<Q", b)[0]


META = metadata()
M, DECOY, KLASS, FIELDS, TYPES, STATICS, OBJ = 0x10000, 0x8000, 0x100000, 0x200000, 0x210000, 0x220000, 0x300000


def game(with_class=True):
    p = FakeProcess()
    s = M + Metadata(META).strings
    p.put(DECOY, META)                            # a stray copy the classes do not point into
    p.put(M, META)
    if with_class:
        klass = bytearray(0x100)
        struct.pack_into("<QQ", klass, 0x10, s + NAME, s + 0)
        struct.pack_into("<Q", klass, 0x80, FIELDS)
        struct.pack_into("<Q", klass, 0xB8, STATICS)
        p.put(KLASS, klass)
        p.put(FIELDS, struct.pack("<QQQiI", s + F_INSTANCE, TYPES, KLASS, 0, 0)
              + struct.pack("<QQQiI", s + F_HEALTH, TYPES + 16, KLASS, 0x18, 0))
        p.put(TYPES, struct.pack("<QI4x", 0, 0x10 | 0x12 << 16)      # static, class
              + struct.pack("<QI4x", 0, 0x0C << 16))                  # float
        p.put(STATICS, struct.pack("<Q", OBJ))
        p.put(OBJ, struct.pack("<Q16xf", KLASS, 75.0))
    return p


class Resolver(unittest.TestCase):
    def test_reads_singleton_and_field_by_name(self):
        il = Il2Cpp(game(), Metadata(META))
        player = il.classes(["Player"])["Player"]
        self.assertEqual(il.base, M)
        obj = il.static(player, "instance")
        self.assertEqual(obj, OBJ)
        self.assertTrue(il.is_a(obj, player))
        self.assertEqual(il.get(obj, player, "health"), 75.0)
        self.assertIsNone(il.get(0, player, "health"))

    def test_not_set_up_yet_is_retry(self):
        self.assertEqual(Il2Cpp(game(with_class=False), Metadata(META)).classes(["Player"]), {})
        with self.assertRaises(GameNotReady):
            Il2Cpp(FakeProcess(), Metadata(META)).classes(["Player"])

    def test_unknown_class_is_a_bug_not_a_retry(self):
        with self.assertRaises(ValueError):
            Il2Cpp(game(), Metadata(META)).classes(["Nope"])


if __name__ == "__main__":
    unittest.main()
