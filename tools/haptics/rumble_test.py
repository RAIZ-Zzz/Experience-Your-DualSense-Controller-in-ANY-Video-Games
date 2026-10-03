"""Can we drive left / right haptics ourselves? Sends Xbox rumble to the DSX virtual pad (XInput slot 0)."""
import ctypes, time
x = ctypes.WinDLL("xinput1_4")
class VIB(ctypes.Structure):
    _fields_ = [("left", ctypes.c_ushort), ("right", ctypes.c_ushort)]

def rumble(l, r):
    x.XInputSetState(0, ctypes.byref(VIB(l, r)))

def pulses(label, l, r, n=4, on=0.08, off=0.35):
    print(label, flush=True)
    for _ in range(n):
        rumble(l, r); time.sleep(on); rumble(0, 0); time.sleep(off)
    time.sleep(1.5)

for k in (3, 2, 1):
    print(f"starting in {k}...", flush=True); time.sleep(1)
pulses("1) LEFT only   (left motor 100%)", 65535, 0)
pulses("2) RIGHT only  (right motor 100%)", 0, 65535)
pulses("3) LEFT heavy  (left 100%, right 30%)", 65535, 20000)
pulses("4) RIGHT heavy (left 30%, right 100%)", 20000, 65535)
pulses("5) BOTH equal", 65535, 65535)
print("6) LEFT held 1.5 s (does the game cut it off?)", flush=True)
rumble(65535, 0); time.sleep(1.5); rumble(0, 0)
print("done")
