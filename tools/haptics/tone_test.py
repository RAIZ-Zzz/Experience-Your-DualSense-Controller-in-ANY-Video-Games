"""Do left-only / right-only low tones become left / right haptics (DSX 'System Audio Capture -> BT haptics')?
Plays through the default output, so you will also hear them."""
import io, math, struct, time, wave, winsound

RATE = 48000

def tone(freq, secs, left, right):
    n = int(RATE * secs)
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / (RATE * 0.005), (n - i) / (RATE * 0.005))       # 5 ms fade in/out, no click
        s = math.sin(2 * math.pi * freq * i / RATE) * env * 0.9 * 32767
        frames += struct.pack("<hh", int(s * left), int(s * right))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(frames))
    return buf.getvalue()

def pulses(label, freq, left, right, n=4, secs=0.08, gap=0.3):
    print(label, flush=True)
    snd = tone(freq, secs, left, right)
    for _ in range(n):
        winsound.PlaySound(snd, winsound.SND_MEMORY); time.sleep(gap)
    time.sleep(1.2)

if __name__ == "__main__":
    for k in (3, 2, 1):
        print(f"starting in {k}...", flush=True); time.sleep(1)
    for f in (60, 100, 160):
        pulses(f"{f} Hz  LEFT only", f, 1, 0)
        pulses(f"{f} Hz  RIGHT only", f, 0, 1)
    pulses("100 Hz  LEFT heavy (left 100%, right 30%)", 100, 1, 0.3)
    pulses("100 Hz  RIGHT heavy (left 30%, right 100%)", 100, 0.3, 1)
    print("done")
