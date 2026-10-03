"""Read-only access to a running Unity IL2CPP game's objects by class and field name: no hooks, no dumper.

global-metadata.dat holds every class and field name. The running game keeps that file mapped in memory and
each runtime class (Il2CppClass) points into it for its name and namespace. So: find the mapped metadata,
find a class by its (name, namespace) pointer pair, then read its FieldInfo array (name, type, offset) and its
static fields. Struct offsets inside Il2CppClass are not hard-coded per Unity version; they are found by
checking pointers against each other, and anything that does not check out is GameNotReady (retry later)."""
import struct

from .hook import GameNotReady

FIELD_INFO_SIZE = 0x20          # name, type, parent, int32 offset, uint32 token (stable across IL2CPP versions)
CLASS_NAME_OFFSET = 0x10        # Il2CppClass: image, gc_desc, name, namespaze, ...
CLASS_SEARCH = 0x200            # bytes of Il2CppClass searched for the fields / static_fields pointers
FIELD_ATTRIBUTE_STATIC = 0x10
VALUE_FORMATS = {0x02: "<?", 0x03: "<H", 0x04: "<b", 0x05: "<B", 0x06: "<h", 0x07: "<H", 0x08: "<i", 0x09: "<I",
                 0x0A: "<q", 0x0B: "<Q", 0x0C: "<f", 0x0D: "<d",
                 0x11: "<i"}    # valuetype: read as an int-backed enum
                                # ponytail: other structs read as int32, add per-field formats if a game needs one
POINTER = "<Q"                  # string, class, array, generic instance, object


class Metadata:
    """Class and field names from global-metadata.dat (versions 38-39: Unity 6000.3)."""

    def __init__(self, data):
        magic, version = struct.unpack_from("<Ii", data)
        if magic != 0xFAB11BAF or version not in (38, 39):
            raise ValueError(f"unsupported metadata (magic {magic:#x}, version {version})")
        sec = [struct.unpack_from("<iii", data, 8 + 12 * i) for i in range(31)]    # (offset, size, count)
        self.data, self.head = data, data[:32]
        self.strings = sec[2][0]
        self.field_off, fsize, fcount = sec[11]
        self.field_rec = fsize // fcount
        self.type_off, tsize, tcount = sec[19]
        self.type_rec = tsize // tcount
        w = (self.type_rec - 68) // 4               # width of the variable-sized type indices (2 or 4)
        self.at_field_start, self.at_field_count = 12 + 4 * w, 48 + 4 * w
        self.types = {}                             # "Namespace.Name" (or "Name") -> [typedef offsets]
        for t in range(tcount):
            b = self.type_off + self.type_rec * t
            name, ns = struct.unpack_from("<ii", data, b)
            ns = self.string(ns)
            self.types.setdefault(f"{ns}.{self.string(name)}" if ns else self.string(name), []).append(b)

    def string(self, index):
        start = self.strings + index
        return self.data[start:self.data.index(b"\0", start)].decode("utf-8", "replace")

    def name_indices(self, cls):
        """[(name index, namespace index, [(field name, field name index)])] for every typedef named `cls`."""
        out = []
        for b in self.types.get(cls, []):
            name, ns = struct.unpack_from("<ii", self.data, b)
            start = struct.unpack_from("<i", self.data, b + self.at_field_start)[0]
            count = struct.unpack_from("<H", self.data, b + self.at_field_count)[0]
            fields = []
            for i in range(start, start + count):
                idx = struct.unpack_from("<i", self.data, self.field_off + self.field_rec * i)[0]
                fields.append((self.string(idx), idx))
            out.append((name, ns, fields))
        return out


class Class:
    def __init__(self, addr, fields):
        self.addr = addr
        self.fields = fields                        # name -> (offset, type code, static)


class Il2Cpp:
    """One attached game process. classes() finds classes once (a memory scan); reads are cheap after that."""

    def __init__(self, proc, metadata):
        self.proc, self.meta = proc, metadata
        self.base = None                            # address of the mapped metadata in the game
        self.static_at = None                       # Il2CppClass offset of static_fields, same for every class

    def _scan(self, needles):
        """{needle: [8-aligned addresses]} in one pass over the game's readable memory."""
        # ponytail: full scan of all committed memory (seconds on a big game), done once per attach;
        # restrict to private read-write regions if it is too slow
        hits = {n: [] for n in needles}
        overlap = max(map(len, needles)) - 1
        for lo, hi in self.proc.regions(0, 1 << 47):
            for pos in range(lo, hi, 1 << 20):
                data = self.proc.read(pos, min((1 << 20) + overlap, hi - pos))
                if not data:
                    continue
                for n in needles:
                    i = data.find(n)
                    while i != -1 and i < 1 << 20:
                        if (pos + i) % 8 == 0:
                            hits[n].append(pos + i)
                        i = data.find(n, i + 1)
        return hits

    def _str(self, base, index):
        return base + self.meta.strings + index

    def classes(self, names):
        """{name: Class} for the classes the game has set up so far (it creates them on first use);
        GameNotReady while the metadata itself is not loaded yet."""
        wanted = {name: self.meta.name_indices(name) for name in names}
        missing = [n for n, v in wanted.items() if not v]
        if missing:
            raise ValueError(f"no such class in the metadata: {', '.join(missing)}")
        bases = [self.base] if self.base else self._scan([self.meta.head])[self.meta.head]
        if not bases:
            raise GameNotReady("IL2CPP metadata not loaded yet")
        # the metadata may sit in memory more than once; the copy the classes point into is the real one
        needles = {struct.pack("<QQ", self._str(b, n), self._str(b, ns)): (b, cls, fields)
                   for b in bases for cls, defs in wanted.items() for n, ns, fields in defs}
        out = {}
        for needle, addrs in self._scan(list(needles)).items():
            base, cls, fields = needles[needle]
            for a in addrs:
                c = self._class(base, a - CLASS_NAME_OFFSET, fields)
                if c:
                    out[cls], self.base = c, base
        return out

    def _class(self, base, klass, fields):
        """Class if `klass` is a set-up Il2CppClass whose FieldInfo array matches `fields`, else None."""
        if not fields:
            return Class(klass, {})
        first = self._str(base, fields[0][1])
        for off in range(0, CLASS_SEARCH, 8):
            arr = self.proc.read_ptr(klass + off)
            if arr and self.proc.read_ptr(arr) == first and self.proc.read_ptr(arr + 0x10) == klass:
                break
        else:
            return None
        out = {}
        for i, (name, idx) in enumerate(fields):
            raw = self.proc.read(arr + FIELD_INFO_SIZE * i, FIELD_INFO_SIZE)
            if raw is None:
                return None
            name_p, type_p, parent, offset = struct.unpack_from("<QQQi", raw)
            bits = self.proc.read(type_p + 8, 4) if type_p else None
            if name_p != self._str(base, idx) or parent != klass or bits is None:
                return None
            bits = struct.unpack("<I", bits)[0]
            out[name] = (offset, (bits >> 16) & 0xFF, bool(bits & FIELD_ATTRIBUTE_STATIC))
        return Class(klass, out)

    def get(self, obj, cls, field):
        """Value of an instance field of object `obj` (pointer for reference types), or None."""
        if not obj:
            return None
        offset, code, static = cls.fields[field]
        if static:
            raise ValueError(f"{field} is static: use static()")
        return self._value(obj + offset, code)

    def static(self, cls, field):
        """Value of a static field, or None while the class has no static storage yet."""
        offset, code, static = cls.fields[field]
        if not static:
            raise ValueError(f"{field} is not static: use get()")
        if self.static_at is None:
            self.static_at = self._find_static_at(cls, offset, code)
            if self.static_at is None:
                return None
        base = self.proc.read_ptr(cls.addr + self.static_at)
        return self._value(base + offset, code) if base else None

    def _find_static_at(self, cls, offset, code):
        """Offset of static_fields in Il2CppClass, learned from a singleton: a static field holding an object
        of its own class (Player.instance -> Player object -> its class pointer is the class itself)."""
        if VALUE_FORMATS.get(code, POINTER) != POINTER:
            return None
        for off in range(0, CLASS_SEARCH, 8):
            base = self.proc.read_ptr(cls.addr + off)
            obj = self.proc.read_ptr(base + offset) if base else None
            if obj and self.proc.read_ptr(obj) == cls.addr:
                return off
        return None

    def _value(self, addr, code):
        fmt = VALUE_FORMATS.get(code, POINTER)
        raw = self.proc.read(addr, struct.calcsize(fmt))
        return None if raw is None else struct.unpack(fmt, raw)[0]

    def is_a(self, obj, cls):
        """Is `obj` a live object of exactly class `cls` (not a stale or reused pointer)?"""
        return bool(obj) and self.proc.read_ptr(obj) == cls.addr
