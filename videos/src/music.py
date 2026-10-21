#!/usr/bin/env python3
# Soft background bed for the 15 s ads: warm pad + electric-piano arpeggio + sine bass + soft kick.
# No noise-based sounds (Polina dislikes hiss). Usage: music.py OUT.wav SECONDS [END_AT]
import sys, wave, math
import numpy as np

SR = 44100
BPM = 96; BEAT = 60 / BPM; BAR = 4 * BEAT
def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
# Fmaj9 - Am7 - Dm9 - Cmaj7(add9), MIDI notes
CHORDS = [[53, 57, 60, 64, 67], [57, 60, 64, 67, 71], [50, 57, 60, 64, 65], [48, 55, 59, 62, 64]]
BASS = [41, 45, 38, 36]

def adsr(n, a, d, s, r):
    e = np.full(n, s, np.float64); ia, idd, ir = int(a * SR), int(d * SR), int(r * SR)
    e[:ia] = np.linspace(0, 1, ia, endpoint=False) if ia else e[:ia]
    e[ia:ia + idd] = np.linspace(1, s, idd, endpoint=False)[:max(0, min(idd, n - ia))]
    if ir: e[-ir:] *= np.linspace(1, 0, ir) ** 2
    return e

def pad(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):                     # three detuned voices, soft harmonics only
        ff = f * 2 ** (det / 12)
        for h, g in ((1, 1.0), (2, 0.28), (3, 0.1)):
            y += g * np.sin(2 * np.pi * ff * h * t + det * 7 + h)
    return y * adsr(n, 0.9, 0.6, 0.75, 0.9) * (0.92 + 0.08 * np.sin(2 * np.pi * 0.25 * t))

def epiano(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 6)) + 0.18 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t * 9)
    return y * np.exp(-t * 3.2) * np.minimum(1, t / 0.004)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.12 * np.sin(2 * np.pi * 2 * f * t)) * adsr(n, 0.02, 0.3, 0.7, 0.25)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 28)) / SR) * np.exp(-t * 9)

def render(total, end_at=None):
    n = int((total + 2) * SR); L = np.zeros(n); R = np.zeros(n)
    def add(sig, t0, gl, gr):
        i = int(t0 * SR)
        if i >= n: return
        j = min(n, i + len(sig)); L[i:j] += sig[:j - i] * gl; R[i:j] += sig[:j - i] * gr
    bars = int(math.ceil(total / BAR)) + 1
    arp = [0, 2, 1, 3, 4, 3, 2, 1]
    for b in range(bars):
        t0 = b * BAR; ch = CHORDS[b % 4]
        for k, m in enumerate(ch): add(pad(hz(m), BAR + 0.9) * 0.05, t0, 0.6 + 0.1 * (k % 2), 0.6 + 0.1 * ((k + 1) % 2))
        add(bass(hz(BASS[b % 4]), BAR * 0.5) * 0.22, t0, 0.7, 0.7)
        add(bass(hz(BASS[b % 4]), BAR * 0.5) * 0.18, t0 + BAR * 0.5, 0.7, 0.7)
        for s in range(8):                              # eighth-note arpeggio, an octave up
            m = ch[arp[s]] + 12; pan = 0.35 + 0.3 * (s % 2)
            add(epiano(hz(m), 1.2) * (0.085 if s % 2 == 0 else 0.06), t0 + s * BEAT / 2, 1 - pan, pan)
        if b >= 1:                                      # soft kick from bar 2 on, beats 1 and 3
            for q in (0, 2): add(kick() * 0.32, t0 + q * BEAT, 0.7, 0.7)
    # simple stereo delay for space (no noise reverb)
    for d, g in ((0.235, 0.22), (0.47, 0.12)):
        k = int(d * SR); L[k:] += R[:-k] * g; R[k:] += L[:-k] * g * 0.9
    y = np.stack([L, R], 1)[:int(total * SR)]
    t = np.arange(len(y)) / SR; env = np.minimum(1, t / 0.6)
    if end_at is not None:                              # resolve and fade under the end logo
        env *= np.clip(1 - (t - end_at) / 2.0, 0, 1) ** 1.5
    y *= env[:, None]; return y / (np.abs(y).max() + 1e-9) * 0.7

def write(out, total, end_at=None):
    y = render(total, end_at)
    with wave.open(out, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((y * 32767).astype("<i2").tobytes())

if __name__ == "__main__":
    write(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else None)
