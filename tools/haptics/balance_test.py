"""Find the left strength that feels equal to right at 100%. Each round: 3 left pulses, then 3 right pulses."""
import ctypes, time
x = ctypes.WinDLL("xinput1_4")
class VIB(ctypes.Structure):
    _fields_ = [("left", ctypes.c_ushort), ("right", ctypes.c_ushort)]

def rumble(l, r):
    x.XInputSetState(0, ctypes.byref(VIB(int(l), int(r))))

def pulses(l, r, n=3, on=0.08, off=0.3):
    for _ in range(n):
        rumble(l, r); time.sleep(on); rumble(0, 0); time.sleep(off)

for k in (3, 2, 1):
    print(f"starting in {k}...", flush=True); time.sleep(1)
for n, pct in enumerate((100, 60, 40, 25, 15, 8), 1):
    print(f"round {n}: LEFT {pct}%  ->  RIGHT 100%", flush=True)
    pulses(65535 * pct / 100, 0)
    time.sleep(0.4)
    pulses(0, 65535)
    time.sleep(2)
print("done - which round felt equal?")
