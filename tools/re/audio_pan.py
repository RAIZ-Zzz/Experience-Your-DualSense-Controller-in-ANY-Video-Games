"""Is the game's sound for an event panned left / right? Records what the PC plays (WASAPI loopback) while a
hooked function runs, then prints left vs right loudness right after each call. Needs: numpy soundcard.

    python tools/re/audio_pan.py game.exe 90 0x1418849c0:8:rcx

Side flips well above 50 % = the sound follows a side (e.g. left / right cannon). Squadrons: 81 % flips,
but only about +-0.1 pan - too weak to come through audio haptics."""
import sys
import threading
import time

import numpy as np
import soundcard as sc

from common import attach, parse_hooks
from dualsense.hook import InstalledSpy, Spy

exe, secs = sys.argv[1], float(sys.argv[2])
(addr, n, reg), = parse_hooks(sys.argv[3:4])
p = attach(exe, write=True)
spy = InstalledSpy.install(p, Spy("event", p.read(addr, 16).hex(" ").upper(), 0, n, reg), addr, 16)
blocks = []


def rec():
    mic = sc.get_microphone(sc.default_speaker().name, include_loopback=True)
    with mic.recorder(samplerate=48000, channels=2) as r:
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < secs:
            blocks.append((time.perf_counter(), r.record(numframes=480)))


th = threading.Thread(target=rec)
th.start()
events, last = [], spy.calls()
try:
    while th.is_alive():
        c = spy.calls()
        if c != last:
            events.append(time.perf_counter())
            last = c
        time.sleep(0.001)
finally:
    spy.remove()

audio = np.concatenate([b for _, b in blocks])
tline = np.concatenate([t - len(b) / 48000 + np.arange(len(b)) / 48000 for t, b in blocks])
pans = []
for t in events:
    seg = audio[(tline >= t) & (tline < t + 0.12)]
    if len(seg):
        left, right = np.sqrt((seg ** 2).mean(axis=0))
        pans.append((right - left) / (right + left + 1e-9))
        print(f"L {left:.3f}  R {right:.3f}  pan {pans[-1]:+.2f}")
flips = sum((a > 0) != (b > 0) for a, b in zip(pans, pans[1:]))
print(f"{len(pans)} events, side flips {flips}/{max(1, len(pans) - 1)} (random ~50%), "
      f"mean |pan| {np.mean(np.abs(pans)) if pans else 0:.2f}")
