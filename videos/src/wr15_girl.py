#!/usr/bin/env python3
# 15 s White Room Group ad, presenter version: the ElevenLabs talking video below, the Luban scenes from
# wr15_luban.py in a panel above, word-by-word subtitles over the presenter.
# Usage: wr15_girl.py preview OUT_PREFIX t1,t2,...   |   wr15_girl.py full OUT.mp4
import os, sys, math, subprocess, glob
from multiprocessing import Pool
os.environ.setdefault("SUB_CY", "1660")
import numpy as np
from PIL import Image
import wr15_luban as L

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE + "/girl_alicante.mp4"
TMP = L.TMP; W, H, FPS = L.W, L.H, 25
VID_END = 15.4; TOTAL = 17.9
PANEL_H = 1040                     # top panel height in split screen
PANEL_SRC_Y = 175                   # rows of the Luban frame shown in the panel start here
SHOT_CUT = 4.0                     # presenter shot change in the source video
def girl_y0(t): return 330 if t < SHOT_CUT else 230   # source row that sits at the panel edge (keeps her head in view)

def girl_frame(t):
    i = min(int(round(t * FPS)), len(GIRL) - 1); return Image.open(GIRL[i]).convert("RGBA")
GIRL = []

def _grad():
    a = np.zeros((H, 1), np.float32); y = np.arange(H)
    a[:, 0] = np.clip((y - 1380) / 540, 0, 1) ** 1.3 * 0.62 + np.clip((330 - y) / 330, 0, 1) * 0.38
    g = np.zeros((H, W, 4), np.uint8); g[..., 3] = (np.repeat(a, W, 1) * 255).astype(np.uint8); return Image.fromarray(g)
GRAD = _grad()

# split amount over time: 0 = presenter full screen, 1 = panel + presenter below
SPLIT = [(0.0, 0), (0.85, 0), (1.2, 1), (11.95, 1), (12.3, 1), (13.95, 1), (14.3, 0)]
def split_k(t):
    for (a, ka), (b, kb) in zip(SPLIT, SPLIT[1:]):
        if a <= t <= b: return L.lerp(ka, kb, L.ease_io((t - a) / (b - a)))
    return 0

# Luban scenes re-timed for this cut: sketch reveal starts when the panel opens, the photo arrives on "Mira esto"
def panel(t):
    if t < 2.95:
        tt = L.clamp((t - 0.9) / 1.1 * 0.95, 0, 0.95) if t < 2.0 else 0.95 + (t - 2.0) * 1.0
        fr = L.sc_hook_at(tt, pin=(t >= 1.0) * L.prog(t, 1.0, 0.45) * (1 - L.ease_io(L.prog(t, 2.4, 0.3))))
    else:
        fr = None
        for i, (a, b, fn) in enumerate(L.SCENES[1:6]):
            if a - L.XF <= t < b:
                img = fn(t); fr = img if fr is None else Image.blend(fr, img, L.ease_io(L.prog(t, a - L.XF, L.XF)))
        if fr is None: fr = L.sc_photos(min(t, 14.2))
        if t < 2.95 + L.XF:
            fr = Image.blend(L.sc_hook_at(0.95 + (t - 2.0)), fr, L.ease_io(L.prog(t, 2.95, L.XF)))
    return fr.crop((0, PANEL_SRC_Y, W, PANEL_SRC_Y + PANEL_H))

def compose(t):
    if t >= VID_END:
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        g = girl_frame(t); k = split_k(t)
        fr = Image.new("RGBA", (W, H), L.BG + (255,))
        if k <= 0.001: fr.alpha_composite(g)
        else:
            y_edge = int(PANEL_H * k); dy = int((PANEL_H - girl_y0(t)) * k)
            fr.alpha_composite(g, (0, dy))
            p = panel(t).crop((0, PANEL_H - y_edge, W, PANEL_H)) if y_edge > 0 else None
            if p: fr.alpha_composite(p, (0, 0))
            line = Image.new("RGBA", (W, 4), L.GOLD + (int(200 * k),)); fr.alpha_composite(line, (0, max(0, y_edge - 2)))
        fr.alpha_composite(GRAD)
        if t >= 13.95:                          # call to action over the presenter
            L.draw_cta(fr, t, 1240, t0=-0.3)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ov.alpha_composite(L.WM, L.WM_POS); L.draw_subs(ov, t); fr.alpha_composite(ov)
    FB0, FB1 = VID_END - 0.35, VID_END + 0.1
    if t >= FB0:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), L.ease_io(L.prog(t, FB0, FB1 - FB0)))
        lk = L.ease_out(L.prog(t, VID_END + 0.1, 1.0)) * (1 - L.ease_io(L.prog(t, TOTAL - 0.7, 0.6)))
        if lk > 0:
            sc = 0.97 + 0.03 * L.ease_out(L.prog(t, VID_END + 0.1, 1.4)); lg = L.END_LOGO
            lg = lg.resize((round(lg.width * sc), round(lg.height * sc)), Image.LANCZOS)
            fr.alpha_composite(L.with_alpha(lg, lk), ((W - lg.width) // 2, (H - lg.height) // 2 - 20))
    return fr.convert("RGB")

def make_sfx(path):
    SR = L.SR; total = np.zeros((int(TOTAL * SR) + SR * 2, 2))
    def put(t, snd, g):
        i = max(0, int(t * SR)); seg = snd * L.db(g); total[i:i + len(seg)] += seg[:len(total) - i]
    pop = L.sfx_pop
    put(1.0, pop(1100, 600, 0.12), -20); put(2.0, pop(1400, 900, 0.1), -20)
    put(3.12, pop(900, 300, 0.18), -16)
    for tt in (4.56, 5.04): put(tt, pop(1000, 600, 0.12), -18)
    for tt in (6.24, 6.96): put(tt + 0.05, pop(1200, 800, 0.1), -18)
    put(8.8, pop(1400, 900, 0.1), -20); put(9.0, pop(1100, 600, 0.12), -20)
    for i in range(5): put(9.55 + i * 0.12, pop(600, 250, 0.14), -19)
    put(10.82, L.sfx_tick(), -15)
    for tt in (11.0, 11.15, 11.3): put(tt, pop(1300, 900, 0.1), -19)
    put(14.62 + 0.3, L.sfx_tick(), -12); put(14.64 + 0.3, pop(1300, 700, 0.12), -15)
    put(VID_END + 0.1, L.sfx_boom(), -12); put(VID_END + 0.15, L.sfx_shimmer(), -24)
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(total, -1, 1) * 32767).astype("<i2").tobytes())

def extract():
    d = TMP + "/girl_frames"; os.makedirs(d, exist_ok=True)
    if not glob.glob(d + "/*.png"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vf", f"fps={FPS},scale={W}:{H}", d + "/g_%04d.png"], check=True)
    GIRL[:] = sorted(glob.glob(d + "/*.png"))
def _frame(i):
    if not GIRL: extract()
    p = f"{TMP}/wr15g_{i:04d}.png"; compose(i / FPS).save(p, compress_level=1); return p
def run(out):
    extract(); sfx = TMP + "/wr15g_sfx.wav"; make_sfx(sfx); n = int(round(TOTAL * FPS))
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/wr15g_%04d.png", "-i", SRC, "-i", sfx,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[v];[2:a]aresample=44100[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        extract()
        for tt in sys.argv[3].split(","): compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
