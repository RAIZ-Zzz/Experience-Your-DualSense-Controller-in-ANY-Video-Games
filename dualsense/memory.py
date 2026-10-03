"""Access to another process's memory (Windows, ctypes). Read-only unless opened with write=True (used by hook.py)."""
import ctypes
import ctypes.wintypes as wt
import re
import struct

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_WRITE = 0x0020
TH32CS_SNAPPROCESS = 0x2
TH32CS_SNAPMODULE = 0x8
TH32CS_SNAPMODULE32 = 0x10
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_EXECUTE_READWRITE = 0x40
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100
INVALID_HANDLE = wt.HANDLE(-1).value

# Never attach while any of these run: reading a protected game can get the account banned.
ANTI_CHEAT_PROCESSES = {"easyanticheat.exe", "easyanticheat_eos.exe"}


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.WriteProcessMemory.argtypes = k32.ReadProcessMemory.argtypes
k32.VirtualProtectEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, ctypes.POINTER(wt.DWORD)]
k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.FlushInstructionCache.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t]


def list_processes():
    """[(pid, exe_name_lowercase)]"""
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())
    out, e = [], PROCESSENTRY32W(dwSize=ctypes.sizeof(PROCESSENTRY32W))
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            out.append((e.th32ProcessID, e.szExeFile.lower()))
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return out


def anti_cheat_running(processes=None):
    return any(name in ANTI_CHEAT_PROCESSES for _, name in (processes or list_processes()))


def pattern_to_regex(pattern):
    """'48 8B ?? 05' -> compiled bytes regex ('??' / '?' = any byte)."""
    parts = [b"." if tok in ("?", "??") else re.escape(bytes([int(tok, 16)])) for tok in pattern.split()]
    return re.compile(b"".join(parts), re.DOTALL)


class Process:
    def __init__(self, pid, write=False):
        self.pid = pid
        access = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        if write:
            access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        self.handle = k32.OpenProcess(access, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.base, self.size, self.module_name, self.path = self._main_module()

    @classmethod
    def find(cls, names, write=False):
        """Attach to the first running process whose exe name is in `names`; None if not running.
        Refuses (RuntimeError) while an anti-cheat process is running."""
        procs = list_processes()
        if anti_cheat_running(procs):
            raise RuntimeError("EasyAntiCheat is running - refusing to read game memory")
        wanted = {n.lower() for n in names}
        pid = next((pid for pid, name in procs if name in wanted), None)
        return cls(pid, write) if pid else None

    def _main_module(self):
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, self.pid)
        if snap == INVALID_HANDLE:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            m = MODULEENTRY32W(dwSize=ctypes.sizeof(MODULEENTRY32W))
            if not k32.Module32FirstW(snap, ctypes.byref(m)):
                raise ctypes.WinError(ctypes.get_last_error())
            return m.modBaseAddr, m.modBaseSize, m.szModule, m.szExePath
        finally:
            k32.CloseHandle(snap)

    def alive(self):
        code = wt.DWORD()
        return bool(k32.GetExitCodeProcess(self.handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE

    def close(self):
        if self.handle:
            k32.CloseHandle(self.handle)
            self.handle = None

    def read(self, addr, size):
        """bytes, or None if the range is not readable."""
        buf = ctypes.create_string_buffer(size)
        n = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.handle, addr, buf, size, ctypes.byref(n)) or n.value != size:
            return None
        return buf.raw

    def write(self, addr, data):
        """Write bytes (also into read-only code pages) and flush the instruction cache."""
        old, n = wt.DWORD(), ctypes.c_size_t()
        if not k32.VirtualProtectEx(self.handle, addr, len(data), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            ok = k32.WriteProcessMemory(self.handle, addr, data, len(data), ctypes.byref(n))
        finally:
            k32.VirtualProtectEx(self.handle, addr, len(data), old.value, ctypes.byref(wt.DWORD()))
        if not ok or n.value != len(data):
            raise ctypes.WinError(ctypes.get_last_error())
        k32.FlushInstructionCache(self.handle, addr, len(data))

    def alloc_near(self, addr, size=0x1000):
        """Executable memory within rel32 jump range below `addr`."""
        for k in range(1, 0x7FFF):                      # 64 KB allocation granularity, up to 2 GB down
            p = k32.VirtualAllocEx(self.handle, (addr & ~0xFFFF) - k * 0x10000, size,
                                   MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
            if p:
                return p
        raise RuntimeError("no free memory within 2 GB of the hook site")

    def read_float(self, addr):
        b = self.read(addr, 4)
        return None if b is None else struct.unpack("<f", b)[0]

    def read_ptr(self, addr):
        b = self.read(addr, 8)
        return None if b is None else struct.unpack("<Q", b)[0]

    def follow(self, base, offsets):
        """Cheat-Engine style pointer chain: [[base]+o1]+o2 ... ; last offset is added, not dereferenced."""
        addr = base
        for off in offsets[:-1]:
            addr = self.read_ptr(addr + off)
            if not addr:
                return None
        return addr + (offsets[-1] if offsets else 0)

    def regions(self, start, end):
        """Committed, readable regions intersecting [start, end)."""
        mbi, addr = MEMORY_BASIC_INFORMATION(), start
        while addr < end and k32.VirtualQueryEx(self.handle, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            base, size = mbi.BaseAddress or 0, mbi.RegionSize
            if mbi.State == MEM_COMMIT and not (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)):
                yield max(base, start), min(base + size, end)
            addr = base + size

    def scan(self, pattern, start=None, size=None, chunk=1 << 20):
        """Addresses where `pattern` matches; defaults to the main module."""
        rx = pattern_to_regex(pattern)
        overlap = len(pattern.split()) - 1
        start = self.base if start is None else start
        end = start + (self.size if size is None else size)
        hits = []
        for lo, hi in self.regions(start, end):
            for pos in range(lo, hi, chunk):
                n = min(chunk + overlap, hi - pos)
                data = self.read(pos, n)
                if data:
                    hits += [pos + m.start() for m in rx.finditer(data) if m.start() < chunk]
        return hits
