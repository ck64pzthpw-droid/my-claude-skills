#!/usr/bin/env python3
# 15 s White Room Group ad on the ElevenLabs voice-over, rebuilt with real Luban Cabin S70 material.
# Usage: wr15_luban.py preview OUT_PREFIX t1,t2,...   |   wr15_luban.py full OUT.mp4
import os, sys, math, subprocess, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.environ.get("IMG_DIR", "/mnt/project-files/site/img")
AUDIO = os.environ.get("VO", HERE + "/vo_alicante.mp3")
TMP = os.environ.get("TMP_DIR", "/tmp")
FONT = "/usr/share/fonts/opentype/inter/"
W, H, FPS = 1080, 1920, 30
TOTAL, VO_END = 18.4, 15.39
SS = 3                                   # supersampling for vector graphics
GOLD = (217, 161, 90); WHITE = (255, 255, 255); BG = (14, 14, 17); PAPER = (246, 244, 239)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def ease_out(x): return 1 - (1 - x) ** 3
def ease_io(x): return 3 * x * x - 2 * x * x * x
def lerp(a, b, k): return a + (b - a) * k
def font(name, size): return ImageFont.truetype(FONT + name, size)
def with_alpha(im, a):
    if a >= 1: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a))); return im
def ss_canvas(w, h, fill=(0, 0, 0, 0)):
    im = Image.new("RGBA", (w * SS, h * SS), fill); return im, ImageDraw.Draw(im)
def ss_done(im, w, h): return im.resize((w, h), Image.LANCZOS)
def cover(path, w, h, cx=0.5, cy=0.5, crop=None):
    im = Image.open(path).convert("RGB")
    if crop: im = im.crop(crop)
    s = max(w / im.width, h / im.height); nw, nh = math.ceil(im.width * s), math.ceil(im.height * s)
    im = im.resize((nw, nh), Image.LANCZOS); x = int((nw - w) * cx); y = int((nh - h) * cy)
    return im.crop((x, y, x + w, y + h))
def zoom(im, z, cx=0.5, cy=0.5):
    w_, h_ = im.size; cw, ch = w_ / z, h_ / z
    x0 = clamp(cx * w_ - cw / 2, 0, w_ - cw); y0 = clamp(cy * h_ - ch / 2, 0, h_ - ch)
    return im.resize((w_, h_), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
def rounded(im, r):
    im = im.convert("RGBA"); m, d = ss_canvas(*im.size)
    d.rounded_rectangle([0, 0, im.width * SS - 1, im.height * SS - 1], r * SS, fill=(255, 255, 255, 255))
    a = ss_done(m, *im.size).getchannel("A"); im.putalpha(Image.fromarray(np.minimum(np.array(a), np.array(im.getchannel("A"))))); return im
def shadow_of(im, blur, a):
    pad = blur * 3; sh = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new("L", sh.size, 0); m.paste(im.getchannel("A"), (pad, pad))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * a))); return sh, pad

# ---------------------------------------------------------------- layout
CW, CH = 980, 620                        # photo card
CARD_Y = 860                             # card centre
SUB_CY, MAXW = int(os.environ.get("SUB_CY", 1330)), 820

def make_bg():
    a = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]; g = np.exp(-(((xx - W / 2) / 900) ** 2 + ((yy - CARD_Y) / 800) ** 2))
    a += g[..., None] * np.array([14, 12, 10], np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
BGI = make_bg()

def put_card(fr, card, cy=CARD_Y, scale=1.0, a=1.0, radius=34, dx=0):
    c = rounded(card, radius)
    if scale != 1.0: c = c.resize((round(c.width * scale), round(c.height * scale)), Image.LANCZOS)
    sh, pad = shadow_of(c, 22, 0.6 * a)
    x = (W - c.width) // 2 + int(dx); y = int(cy - c.height / 2)
    fr.alpha_composite(sh, (x - pad, y - pad + 18)); fr.alpha_composite(with_alpha(c, a), (x, y))

# ---------------------------------------------------------------- logo
def logo(scale, with_text=True, stacked=False):
    s = SS * scale; size = 32
    ic, d = ss_canvas(int(size * scale) + 2, int(size * scale) + 2)
    P = lambda x, y: (x * s, y * s); lw = max(2, int(1.3 * s))
    for path in ([(16, 2), (29, 9.5), (29, 22.5), (16, 30), (3, 22.5), (3, 9.5), (16, 2)],
                 [(3, 9.5), (16, 17), (29, 9.5)], [(16, 17), (16, 30)], [(9.5, 5.8), (22.5, 13.2), (22.5, 26.2)]):
        d.line([P(*p) for p in path], fill=WHITE + (255,), width=lw, joint="curve")
    icon = ss_done(ic, int(size * scale) + 2, int(size * scale) + 2)
    if not with_text: return icon
    f1 = font("Inter-SemiBold.otf", int(11 * scale)); f2 = font("Inter-Medium.otf", int(6.5 * scale))
    def spaced(txt, f, tr):
        w = sum(f.getlength(c) for c in txt) + tr * (len(txt) - 1)
        im = Image.new("RGBA", (int(w) + 4, int(f.size * 1.3)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 0
        for c in txt: dd.text((x, 0), c, font=f, fill=WHITE + (255,)); x += f.getlength(c) + tr
        return im
    t1 = spaced("WHITEROOM", f1, 0.28 * f1.size); t2 = spaced("GROUP", f2, 0.6 * f2.size)
    if stacked:
        wd = max(icon.width, t1.width); out = Image.new("RGBA", (wd, icon.height + t1.height + t2.height + int(14 * scale / 4)), (0, 0, 0, 0))
        out.alpha_composite(icon, ((wd - icon.width) // 2, 0)); y = icon.height + int(10 * scale / 4)
        out.alpha_composite(t1, ((wd - t1.width) // 2, y)); out.alpha_composite(t2, ((wd - t2.width) // 2, y + t1.height))
        return out
    gap = int(8 * scale); wd = icon.width + gap + max(t1.width, t2.width); ht = max(icon.height, t1.height + t2.height)
    out = Image.new("RGBA", (wd, ht), (0, 0, 0, 0)); out.alpha_composite(icon, (0, (ht - icon.height) // 2))
    ty = (ht - t1.height - t2.height) // 2 + 1
    out.alpha_composite(t1, (icon.width + gap, ty)); out.alpha_composite(t2, (icon.width + gap + (t1.width - t2.width) // 2, ty + t1.height))
    return out
WM = with_alpha(logo(2.4), 0.92); WM_POS = ((W - WM.width) // 2, 92)
END_LOGO = logo(7.5, stacked=True)

# ---------------------------------------------------------------- assets
def pencil(img):
    g = ImageOps.grayscale(img); inv = ImageOps.invert(g).filter(ImageFilter.GaussianBlur(10))
    a = np.array(g, np.float32); b = np.array(inv, np.float32)
    sk = np.clip(a * 255 / np.maximum(1, 255 - b), 0, 255)
    sk = 255 - (255 - sk) * 1.35                              # darker graphite
    edges = np.array(g.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6)), np.float32)
    sk = np.clip(sk - edges * 0.9, 0, 255)
    paper = np.array(PAPER, np.float32)[None, None, :]
    rgb = paper * (sk[..., None] / 255.0) + np.array([40, 40, 46], np.float32) * (1 - sk[..., None] / 255.0)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))

HERO = cover(IMG + "/hero-s70.jpg", CW * 2, CH * 2, 0.5, 0.55)
# Polina's generated sketches; the S70 one is pre-aligned to hero-s70.jpg (refs/sketch_s70_aligned.png)
SKETCH = cover(HERE + "/refs/sketch_s70_aligned.png", CW * 2, CH * 2, 0.5, 0.55)
_fs = ImageOps.grayscale(cover(HERE + "/refs/sketch_frame.png", CW, CH, 0.5, 0.45))
FRAME_INK = Image.fromarray(np.clip((255 - np.array(_fs, np.float32)) * 1.5, 0, 255).astype(np.uint8))
FRAME = cover(IMG + "/insulation.jpg", CW * 2, CH * 2, 0.45, 0.6)
LIVING = cover(IMG + "/s70-living.jpg", CW * 2, CH * 2, 0.5, 0.55)   # straight lens; 2bed-living is wide-angle
KITCHEN = cover(IMG + "/s70-kitchen.jpg", CW, CH * 2, 0.5, 0.42)
BATH = cover(IMG + "/s70-bath.jpg", CW, CH * 2, 0.55, 0.45)
END1 = cover(IMG + "/wr-hero.jpg", CW * 2, CH * 2, 0.5, 0.7, crop=(0, 470, 1600, 1289))
END2 = cover(IMG + "/hero-k70.jpg", CW * 2, CH * 2, 0.5, 0.5)

# plan: real S70 two-bedroom layout, inverted to light lines on the dark card
def make_plan():
    p = Image.open(IMG + "/s70-2bed-plan.jpg").convert("L")
    d = ImageDraw.Draw(p); d.rectangle([860, 485, 1385, 540], fill=255)      # drop the vendor caption
    p = p.crop((100, 30, 1350, 570))                                            # 1250 x 540
    a = np.array(p, np.float32) / 255.0
    ink = np.clip((1 - a) * 1.6, 0, 1)                                          # lines/walls -> 1
    rgb = np.array(BG, np.float32) * 1.5 * (1 - ink[..., None]) + np.array([236, 234, 228], np.float32) * ink[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), ink
PLAN, PLAN_INK = make_plan()
PX0, PY0 = 100, 30                                                              # crop origin in source px
ROOMS = {"bed1": (1012, 152, 1314, 444), "bed2": (209, 152, 509, 444),
         "kit": (709, 152, 1002, 444), "bath": (521, 152, 704, 362)}

# ---------------------------------------------------------------- subtitles
WL = [("Tu", 0.0), ("primera", 0.32), ("casa", 0.56), ("en", 0.80), ("Alicante?", 0.96),
      ("Mira", 2.0), ("esto", 2.4), ("38", 3.12), ("metros,", 3.84),
      ("una", 4.56), ("o", 4.88), ("dos", 5.04), ("habitaciones,", 5.28),
      ("cocina", 6.24), ("y", 6.8), ("baño", 6.96), ("completos,", 7.44),
      ("estructura", 8.32), ("de", 8.88), ("acero,", 9.04), ("buen", 9.6), ("aislamiento", 9.84),
      ("y", 10.56), ("casa", 10.8), ("inteligente", 11.2),
      ("Tu", 12.16), ("casa,", 12.4), ("sin", 12.88), ("hipoteca", 13.2), ("eterna", 13.84)]
CH_TXT = ["Tu primera casa / =en Alicante?", "Mira / =esto", "=38 metros,", "una o dos / =habitaciones,",
          "=cocina y baño / completos,", "estructura de / =acero,", "buen / =aislamiento", "y casa / =inteligente",
          "Tu casa, / =sin hipoteca / eterna"]
F_SM = font("Inter-Bold.otf", 46); BIG_FONT = FONT + "InterDisplay-Bold.otf"
def tw(f, s, tr): return sum(f.getlength(c) for c in s) + tr * (len(s) - 1)
class Chunk: pass
CHUNKS = []; _wi = 0
for txt in CH_TXT:
    c = Chunk(); rows = []
    for ln in txt.split("/"):
        ln = ln.strip(); big = ln.startswith("="); row = []
        for w in ln.lstrip("=").split():
            assert WL[_wi][0] == w, (WL[_wi], w); row.append(WL[_wi]); _wi += 1
        rows.append((big, row))
    c.rows = rows; c.start = rows[0][1][0][1] - 0.05; CHUNKS.append(c)
for a, b in zip(CHUNKS, CHUNKS[1:]): a.end = b.start
CHUNKS[-1].end = 14.3
for c in CHUNKS:
    lay = []
    for big, row in c.rows:
        if big:
            s_ = " ".join(w for w, _ in row); size = 108
            while size > 54:
                f = ImageFont.truetype(BIG_FONT, size); tr = -3.0 * size / 112
                if tw(f, s_, tr) <= MAXW: break
                size -= 2
            lay.append((big, row, f, tr, size * 0.98))
        else: lay.append((big, row, F_SM, -0.4, 56))
    widths = [tw(f, " ".join(w for w, _ in row), tr) for big, row, f, tr, lh in lay]
    x0 = (W - max(widths)) / 2; th = sum(l[4] for l in lay); y = SUB_CY - th / 2; items = []
    for big, row, f, tr, lh in lay:
        x = x0; sp = f.getlength(" ") + tr; yoff = -lh * 0.12 if big else 0
        for w, ts in row:
            items.append((w.rstrip("."), ts, big, f, tr, x, y + yoff)); x += tw(f, w, tr) + sp
        y += lh
    c.items = items

def draw_subs(layer, t):
    for c in CHUNKS:
        if not (c.start <= t < c.end): continue
        out = 1 - ease_io(prog(t, c.end - 0.1, 0.1))
        txt = Image.new("RGBA", (W, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(txt); y0 = SUB_CY - 260
        for w, ts, big, f, tr, x, y in c.items:
            k = prog(t, ts - 0.04, 0.2 if big else 0.14)
            if k <= 0: continue
            k = ease_out(k)
            if big: a = int(255 * (0.35 + 0.65 * k)); g = int(170 + 85 * k); col = (g, g, g, a); dy = (1 - k) * 26
            else: col = (255, 255, 255, int(255 * k)); dy = (1 - k) * 12
            xx = x
            for ch in w: d.text((xx, y - y0 + dy), ch, font=f, fill=col); xx += f.getlength(ch) + tr
        a = txt.getchannel("A"); sh = Image.new("RGBA", txt.size, (0, 0, 0, 0))
        sh.putalpha(a.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.6 * out)))
        if out < 1: txt.putalpha(a.point(lambda v: int(v * out)))
        layer.alpha_composite(sh, (0, y0 + 4)); layer.alpha_composite(txt, (0, y0))

# ---------------------------------------------------------------- small graphics
def check_badge(sz, k):
    if k <= 0: return Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    im, d = ss_canvas(sz, sz); s = SS; r = sz / 2 * s * (0.7 + 0.3 * ease_out(clamp(k * 2)))
    c0 = sz / 2 * s; d.ellipse([c0 - r, c0 - r, c0 + r, c0 + r], fill=GOLD + (255,))
    kk = clamp(k * 1.6 - 0.4)
    if kk > 0:
        p0, p1, p2 = (0.28 * sz * s, 0.52 * sz * s), (0.43 * sz * s, 0.66 * sz * s), (0.72 * sz * s, 0.36 * sz * s)
        L1 = math.dist(p0, p1); L2 = math.dist(p1, p2); L = (L1 + L2) * ease_out(kk); pts = [p0]
        if L <= L1: pts.append((lerp(p0[0], p1[0], L / L1), lerp(p0[1], p1[1], L / L1)))
        else: pts += [p1, (lerp(p1[0], p2[0], (L - L1) / L2), lerp(p1[1], p2[1], (L - L1) / L2))]
        d.line(pts, fill=(20, 20, 22, 255), width=int(sz * 0.1 * s), joint="curve")
    return ss_done(im, sz, sz)

def chip(label, k, cy, icon="pin"):
    if k <= 0: return None
    f = font("Inter-SemiBold.otf", 32); txt = " ".join(label); tw_ = f.getlength(txt)
    wch, hch = int(tw_ + 110), 74; im, d = ss_canvas(wch, hch); s = SS
    d.rounded_rectangle([0, 0, wch * s - 1, hch * s - 1], hch * s / 2, fill=(255, 255, 255, 238))
    px, py = 44 * s, 37 * s
    if icon == "pin":
        d.ellipse([px - 16 * s, py - 22 * s, px + 16 * s, py + 10 * s], fill=GOLD + (255,))
        d.polygon([(px - 13 * s, py + 2 * s), (px + 13 * s, py + 2 * s), (px, py + 25 * s)], fill=GOLD + (255,))
        d.ellipse([px - 6.5 * s, py - 12.5 * s, px + 6.5 * s, py + 0.5 * s], fill=(255, 255, 255, 255))
    else:
        d.ellipse([px - 16 * s, py - 16 * s, px + 16 * s, py + 16 * s], fill=GOLD + (255,))
    c = ss_done(im, wch, hch); ImageDraw.Draw(c).text((78, 17), txt, font=f, fill=(24, 24, 26, 255))
    sc = 0.85 + 0.15 * ease_out(k); c = c.resize((round(wch * sc), round(hch * sc)), Image.LANCZOS)
    return with_alpha(c, ease_out(k)), ((W - c.width) // 2, int(cy - c.height / 2 + (1 - ease_out(k)) * 20))

def wipe(base, top, x, soft=80, line=True):
    """reveal `top` over `base` left of x (card px) with a soft edge and a gold scan line"""
    w, h = base.size; m = np.clip((x - np.arange(w)[None, :]) / soft, 0, 1)
    t = top.convert("RGBA"); t.putalpha(Image.fromarray((np.repeat(m, h, 0) * 255).astype(np.uint8)))
    out = base.convert("RGBA"); out.alpha_composite(t)
    if line and 0 < x < w + soft:
        im, d = ss_canvas(w, h); X = (x - soft / 2) * SS
        d.line([(X, 0), (X, h * SS)], fill=GOLD + (235,), width=4 * SS); out.alpha_composite(ss_done(im, w, h))
    return out

def card_of(big, z, cx=0.5, cy=0.5): return zoom(big, z, cx, cy).resize((CW, CH), Image.LANCZOS).convert("RGBA")

# ---------------------------------------------------------------- scenes
def sc_hook(t):                       # 0 - 2.95  sketch draws in, becomes the real S70, Alicante pin, push-in
    return sc_hook_at(t)
def sc_hook_at(t, pin=None):
    fr = BGI.copy()
    z = 1.0 + 0.04 * prog(t, 0, 2.0) + 0.16 * ease_io(prog(t, 2.0, 0.9))
    paper = Image.new("RGBA", (CW, CH), PAPER + (255,))
    c = wipe(paper, card_of(SKETCH, z, 0.5, 0.55), ease_io(prog(t, 0.0, 0.8)) * (CW + 140), 140, line=False)
    kp = ease_io(prog(t, 0.95, 0.6))
    if kp > 0: c = wipe(c, card_of(HERO, z, 0.5, 0.55), kp * (CW + 70), 70, line=kp < 1)
    kin = ease_out(prog(t, 0.0, 0.45))
    put_card(fr, c, scale=0.94 + 0.06 * kin + 0.05 * ease_io(prog(t, 2.0, 0.9)), a=kin)
    r = chip("ALICANTE", prog(t, 0.96, 0.45) * (1 - ease_io(prog(t, 2.0, 0.3))) if pin is None else pin, CARD_Y - CH / 2 - 70)
    if r: fr.alpha_composite(*r)
    return fr

PLW = CW; PLH = round(PLAN.height * CW / PLAN.width)       # plan drawn at card width
def plan_xy(x, y): return ((x - PX0) * PLW / PLAN.width, (y - PY0) * PLH / PLAN.height)
F_BIG = ImageFont.truetype(BIG_FONT, 190); F_M2 = ImageFont.truetype(BIG_FONT, 92)
def sc_plan(t):                       # 2.95 - 7.85  38 m2 counter, plan, bedrooms 1/2, kitchen + bath ticks
    fr = BGI.copy(); py = CARD_Y + 120
    # plan draws in left -> right, then stays
    kd = ease_io(prog(t, 2.95, 0.9))
    pl = PLAN.resize((PLW, PLH), Image.LANCZOS).convert("RGBA")
    m = np.clip((kd * (PLW + 120) - np.arange(PLW)[None, :]) / 120, 0, 1)
    ink = np.array(Image.fromarray((PLAN_INK * 255).astype(np.uint8)).resize((PLW, PLH), Image.LANCZOS), np.float32) / 255
    pl.putalpha(Image.fromarray((np.clip(ink * 1.2, 0, 1) * np.repeat(m, PLH, 0) * 255).astype(np.uint8)))
    fade = 1 - ease_io(prog(t, 7.55, 0.3))
    card = Image.new("RGBA", (PLW, PLH + 40), (20, 20, 23, 255)); card.alpha_composite(pl, (0, 20))
    ov = Image.new("RGBA", card.size, (0, 0, 0, 0))
    for key, t0, num in (("bed1", 4.56, "1"), ("bed2", 5.04, "2")):
        k = ease_out(prog(t, t0, 0.35)) * (1 - ease_io(prog(t, 6.05, 0.3)))
        if k <= 0: continue
        x0, y0 = plan_xy(*ROOMS[key][:2]); x1, y1 = plan_xy(*ROOMS[key][2:]); y0 += 20; y1 += 20
        im, d = ss_canvas(*card.size); s = SS
        d.rectangle([x0 * s, y0 * s, x1 * s, y1 * s], fill=GOLD + (int(70 * k),), outline=GOLD + (int(255 * k),), width=3 * s)
        cx, cy = (x0 + x1) / 2 * s, (y0 + y1) / 2 * s; r = 40 * s * (0.8 + 0.2 * k)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD + (int(255 * k),)); ov.alpha_composite(ss_done(im, *card.size))
        f = ImageFont.truetype(BIG_FONT, 52); ImageDraw.Draw(ov).text(((x0 + x1) / 2 - f.getlength(num) / 2, (y0 + y1) / 2 - 33), num, font=f, fill=(20, 20, 22, int(255 * k)))
    for key, t0 in (("kit", 6.24), ("bath", 6.96)):
        k = prog(t, t0, 0.5)
        if k <= 0: continue
        x0, y0 = plan_xy(*ROOMS[key][:2]); x1, y1 = plan_xy(*ROOMS[key][2:]); y0 += 20; y1 += 20
        im, d = ss_canvas(*card.size)
        d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=GOLD + (int(45 * ease_out(k)),), outline=GOLD + (int(255 * ease_out(k)),), width=3 * SS)
        ov.alpha_composite(ss_done(im, *card.size)); b = check_badge(58, k); ov.alpha_composite(b, (int(x1 - 36), int(y0 - 24)))
    card.alpha_composite(ov)
    kin = ease_out(prog(t, 2.95, 0.4))
    put_card(fr, card, cy=py, a=kin * fade, radius=26)
    # kitchen + bath photos rise above the plan
    for img, t0, dx in ((KITCHEN, 6.24, -250), (BATH, 6.96, 250)):
        k = ease_out(prog(t, t0, 0.45))
        if k <= 0: continue
        ph = zoom(img, 1.0 + 0.05 * prog(t, t0, 1.6)).resize((440, 360), Image.LANCZOS)
        ph = rounded(ph, 24); sh, pad = shadow_of(ph, 18, 0.6 * k * fade)
        x = W // 2 + dx - 220; y = int(py - PLH / 2 - 360 - 34 + (1 - k) * 60)
        fr.alpha_composite(sh, (x - pad, y - pad + 14)); fr.alpha_composite(with_alpha(ph, k * fade), (x, y))
        b = check_badge(70, prog(t, t0 + 0.15, 0.5)); fr.alpha_composite(with_alpha(b, fade), (x + 440 - 52, y - 18))
    # 38 m2 counter above the plan
    kc = prog(t, 3.1, 0.7)
    if kc > 0:
        a = ease_out(prog(t, 3.1, 0.3)) * (1 - ease_io(prog(t, 4.45, 0.3)))
        if a > 0:
            n = str(int(round(38 * ease_out(kc)))); w1 = F_BIG.getlength(n); w2 = F_M2.getlength("m²"); x0 = (W - (w1 + 18 + w2)) / 2
            lab = Image.new("RGBA", (W, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(lab)
            d.text((x0, 10), n, font=F_BIG, fill=GOLD + (255,)); d.text((x0 + w1 + 18, 84), "m²", font=F_M2, fill=(255, 255, 255, 235))
            fr.alpha_composite(with_alpha(lab, a), (0, int(py - PLH / 2 - 300 + (1 - a) * 14)))
    return fr

def sc_steel(t):                      # 7.85 - 9.6  gold wireframe of the frame -> real steel frame in the factory
    fr = BGI.copy(); z = 1.04 + 0.08 * prog(t, 7.6, 2.2)
    photo = card_of(FRAME, z, 0.45, 0.55)
    g = zoom(FRAME_INK, 1.0 + 0.06 * prog(t, 7.6, 2.0))
    line = Image.new("RGBA", (CW, CH), (18, 18, 21, 255)); gl = Image.new("RGBA", (CW, CH), GOLD + (255,))
    kd = ease_io(prog(t, 7.6, 0.5)); m = np.clip((kd * (CW + 160) - np.arange(CW)[None, :]) / 160, 0, 1)
    gl.putalpha(Image.fromarray((np.array(g, np.float32) / 255 * np.repeat(m, CH, 0) * 255).astype(np.uint8))); line.alpha_composite(gl)
    kp = ease_io(prog(t, 8.05, 0.4))
    c = wipe(line, photo, kp * (CW + 70), 70, line=0 < kp < 1) if kp > 0 else line
    put_card(fr, c)
    r = chip("ACERO", prog(t, 8.45, 0.3) * (1 - ease_io(prog(t, 9.1, 0.12))), CARD_Y - CH / 2 - 70, icon="dot")
    if r: fr.alpha_composite(*r)
    return fr

LAYERS = [("Aluminio", (200, 203, 210), 9.27), ("PU 50 mm", GOLD, 9.35), ("Acero", (120, 124, 132), 9.43),
          ("PU 50 mm", GOLD, 9.51), ("Interior", (240, 238, 232), 9.59)]
def sc_insul(t):                      # 9.6 - 10.6  wall section: layers slide in, heat waves stop at the wall
    fr = BGI.copy(); ch = CH; im, d = ss_canvas(CW, ch, (20, 20, 23, 255)); s = SS
    widths = [44, 190, 56, 190, 60]; x = (CW - 540) // 2 + 60; top, bot = 80, ch - 120; f = font("Inter-SemiBold.otf", 28)
    labels = []
    for (name, col, st), wd in zip(LAYERS, widths):
        k = ease_out(prog(t, st, 0.22))
        if k > 0:
            dy = (1 - k) * 90; a = int(255 * k)
            d.rectangle([x * s, (top - dy) * s, (x + wd) * s, (bot - dy) * s], fill=col + (a,))
            if col == GOLD:   # foam texture
                for j in range(14):
                    yy = top - dy + 10 + j * (bot - top - 20) / 13
                    d.line([((x + 10) * s, yy * s), ((x + wd - 10) * s, (yy + 12) * s)], fill=(255, 255, 255, int(110 * k)), width=2 * s)
            labels.append((name, x + wd / 2, k))
        x += wd
    # heat waves from the left, stopping at the outer skin
    for i in range(7):
        u = (t - 9.65 - i * 0.2) / 0.6
        if 0 < u < 1:
            a = int(230 * math.sin(math.pi * u)); yy = (190 + (i % 3) * 110) * s; x0 = lerp(40, 330, ease_out(u)) * s
            pts = [(x0 + j * 9 * s, yy + math.sin(j * 0.9 + t * 9) * 10 * s) for j in range(12)]
            d.line(pts, fill=(255, 120, 70, a), width=6 * s)
    d.line([(60 * s, (bot + 18) * s), ((CW - 60) * s, (bot + 18) * s)], fill=(255, 255, 255, 40), width=2 * s)
    c = ss_done(im, CW, ch); dd = ImageDraw.Draw(c)
    for i, (name, cx, k) in enumerate(labels):       # labels alternate above/below so they never collide
        tw_ = f.getlength(name); y = bot + 40 if i % 2 == 0 else top - 58
        dd.text((cx - tw_ / 2, y), name, font=f, fill=(255, 255, 255, int(230 * k)))
    put_card(fr, c)
    return fr

def sc_smart(t):                      # 10.95 - 12.0  real S70 interior + smart-home app card, switches turn on
    fr = BGI.copy(); z = 1.02 + 0.06 * prog(t, 10.7, 1.6)
    on = [prog(t, t0, 0.2) for t0 in (11.15, 11.28, 11.41)]
    c = card_of(LIVING, z)
    c = ImageEnhance.Brightness(c.convert("RGB")).enhance(0.55 + 0.5 * ease_out(on[0])).convert("RGBA")
    if on[0] > 0: c.alpha_composite(Image.new("RGBA", (CW, CH), (255, 196, 120, int(36 * on[0]))))
    # app panel slides up into the card
    pw, ph = 470, 470; ki = ease_out(prog(t, 10.9, 0.35))
    im, d = ss_canvas(pw, ph); s = SS
    d.rounded_rectangle([0, 0, pw * s - 1, ph * s - 1], 40 * s, fill=(255, 255, 255, 246))
    pnl = ss_done(im, pw, ph); dd = ImageDraw.Draw(pnl)
    f1 = font("Inter-Bold.otf", 34); f2 = font("Inter-SemiBold.otf", 30); f3 = font("Inter-Medium.otf", 24)
    dd.text((40, 34), "Mi casa", font=f1, fill=(24, 24, 26, 255))
    dd.text((40, 80), "WhiteRoom Smart", font=f3, fill=(140, 140, 146, 255))
    rows = [("Luces", "Encendidas"), ("Clima", "22 °C"), ("Cerradura", "Cerrada")]
    im2, d2 = ss_canvas(pw, ph)
    for i, ((lab, val), k) in enumerate(zip(rows, on)):
        y = 140 + i * 106; x = 28; w = pw - 56
        d2.rounded_rectangle([x * s, y * s, (x + w) * s, (y + 92) * s], 24 * s, fill=(244, 243, 239, 255))
        tx, ty = x + w - 112, y + 23; e = ease_io(k)
        d2.rounded_rectangle([tx * s, ty * s, (tx + 88) * s, (ty + 46) * s], 23 * s,
            fill=tuple(int(lerp(a, b, e)) for a, b in zip((206, 206, 210), GOLD)) + (255,))
        cx = lerp(tx + 23, tx + 65, e); d2.ellipse([(cx - 18) * s, (ty + 5) * s, (cx + 18) * s, (ty + 41) * s], fill=(255, 255, 255, 255))
    rl = ss_done(im2, pw, ph); pnl.alpha_composite(rl); dd = ImageDraw.Draw(pnl)
    for i, ((lab, val), k) in enumerate(zip(rows, on)):
        y = 140 + i * 106
        dd.text((54, y + 14), lab, font=f2, fill=(24, 24, 26, 255))
        dd.text((54, y + 52), val if k > 0.5 else "—", font=f3, fill=(GOLD if k > 0.5 else (150, 150, 155)) + (255,))
    sh, pad = shadow_of(pnl, 20, 0.5 * ki)
    px = CW - pw - 40; py_ = int(CH - ph - 40 + (1 - ki) * 160)
    c.alpha_composite(sh, (px - pad, py_ - pad + 12)); c.alpha_composite(with_alpha(pnl, ki), (px, py_))
    put_card(fr, c)
    return fr

def sc_photos(t):                     # 12.0 - 14.27  "Tu casa, sin hipoteca eterna"
    fr = BGI.copy(); c = Image.new("RGBA", (CW, CH), (20, 20, 23, 255))
    k = 0.0   # one photo only: the smart-home card keeps most of this time
    if k < 1: c.alpha_composite(card_of(END1, 1.0 + 0.08 * prog(t, 13.07, 1.2)), (int(-k * CW * 0.35), 0))
    if k > 0: c.alpha_composite(card_of(END2, 1.0 + 0.06 * prog(t, 13.55, 1.0)), (int((1 - k) * CW), 0))
    put_card(fr, c)
    return fr

F_BTN = font("Inter-Bold.otf", 66)
def sc_cta(t):                        # 14.27 - 15.9  "¡Escríbenos!"
    return draw_cta(BGI.copy(), t, H // 2)
def draw_cta(fr, t, cy, t0=0.0):
    t = t - t0
    kin = ease_out(prog(t, 14.3, 0.45)); press = math.sin(math.pi * prog(t, 14.62, 0.22)) if 14.62 <= t <= 14.84 else 0
    bw, bh = 700, 166; im, d = ss_canvas(bw, bh)
    d.rounded_rectangle([0, 0, bw * SS - 1, bh * SS - 1], bh * SS / 2, fill=(255, 255, 255, 255))
    btn = ss_done(im, bw, bh); txt = "Escríbenos!"
    ImageDraw.Draw(btn).text(((bw - F_BTN.getlength(txt)) / 2, 40), txt, font=F_BTN, fill=(20, 20, 22, 255))
    sc = (0.85 + 0.15 * kin) * (1 - 0.06 * press); b = btn.resize((round(bw * sc), round(bh * sc)), Image.LANCZOS)
    sh, pad = shadow_of(b, 26, 0.5 * kin); x, y = (W - b.width) // 2, int(cy - b.height / 2)
    fr.alpha_composite(sh, (x - pad, y - pad + 18)); fr.alpha_composite(with_alpha(b, kin), (x, y))
    rp = prog(t, 14.62, 0.6); kc = prog(t, 14.25, 0.37); kx = 1 - ease_io(prog(t, 15.05, 0.3))
    if kc > 0 and kx > 0:
        x_ = lerp(980, 820, ease_io(kc)); y_ = lerp(cy + 460, cy + 40, ease_io(kc))
        im, d = ss_canvas(330, 330); c0 = 165 * SS; r = 42 * SS * (1 - 0.18 * press)
        d.ellipse([c0 - r, c0 - r, c0 + r, c0 + r], fill=GOLD + (int(150 * kx),), outline=GOLD + (int(255 * kx),), width=10 * SS)
        if 0 < rp < 1:
            R_ = (42 + 105 * ease_out(rp)) * SS; d.ellipse([c0 - R_, c0 - R_, c0 + R_, c0 + R_], outline=GOLD + (int(220 * (1 - rp) * kx),), width=9 * SS)
        fr.alpha_composite(ss_done(im, 330, 330), (int(x_ - 165), int(y_ - 165)))
    return fr

SCENES = [(0.0, 2.95, sc_hook), (2.95, 7.85, sc_plan), (7.85, 9.5, sc_steel), (9.5, 11.05, sc_insul),
          (11.05, 13.35, sc_smart), (13.35, 14.27, sc_photos), (14.27, 99, sc_cta)]
XF = 0.28
def compose(t):
    if t >= 15.6: fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        fr = None
        for i, (a, b, fn) in enumerate(SCENES):
            if a - (XF if i else 0) <= t < b:
                img = fn(t)
                fr = img if fr is None else Image.blend(fr, img, ease_io(prog(t, a - XF, XF)))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ov.alpha_composite(WM, WM_POS); draw_subs(ov, t); fr.alpha_composite(ov)
    FB0, FB1 = 15.45, 15.95
    if t >= FB0:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), ease_io(prog(t, FB0, FB1 - FB0)))
        lk = ease_out(prog(t, 15.95, 1.0)) * (1 - ease_io(prog(t, TOTAL - 0.7, 0.6)))
        if lk > 0:
            sc = 0.97 + 0.03 * ease_out(prog(t, 15.95, 1.4))
            lg = END_LOGO.resize((round(END_LOGO.width * sc), round(END_LOGO.height * sc)), Image.LANCZOS)
            fr.alpha_composite(with_alpha(lg, lk), ((W - lg.width) // 2, (H - lg.height) // 2 - 20))
    return fr.convert("RGB")

# ---------------------------------------------------------------- sound
SR = 44100
def db(g): return 10 ** (g / 20)
def env(n, att, rel):
    e = np.ones(n); a = int(att * SR); r = int(rel * SR)
    if a: e[:a] = np.linspace(0, 1, a)
    if r: e[-r:] *= np.linspace(1, 0, r) ** 2
    return e
RNG = np.random.default_rng(7)
def sfx_whoosh(d=0.55, f0=300, f1=2600):
    n = int(d * SR); x = RNG.standard_normal(n); t = np.arange(n) / SR
    fc = f0 * (f1 / f0) ** (np.sin(np.pi * t / d) ** 1.2)
    # time-varying one-pole low-pass via block processing
    y = np.zeros(n); prev = 0.0; blk = 256
    for i in range(0, n, blk):
        k = 1 - math.exp(-2 * math.pi * fc[i] / SR); seg = x[i:i + blk]; out = np.empty(len(seg))
        for j, v in enumerate(seg): prev += k * (v - prev); out[j] = prev
        y[i:i + blk] = out
    y *= np.sin(np.pi * t / d) ** 2; y /= np.abs(y).max() + 1e-9
    return np.stack([y * 0.9, y], 1)
def sfx_pop(f0=1000, f1=500, d=0.12):
    n = int(d * SR); t = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-t * 40)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30); return np.stack([y, y], 1)
def sfx_tick():
    n = int(0.03 * SR); t = np.arange(n) / SR; y = (RNG.standard_normal(n) * 0.5 + np.sin(2 * np.pi * 3200 * t)) * np.exp(-t * 300)
    return np.stack([y, y], 1)
def sfx_reveal():
    d = 0.9; n = int(d * SR); t = np.arange(n) / SR
    y = sfx_whoosh(d, 600, 6000)[:, 0] * (t / d) ** 2
    hit = int(0.75 * SR); y[hit:] += np.sin(2 * np.pi * 1760 * t[:n - hit]) * np.exp(-t[:n - hit] * 14) * 0.5
    return np.stack([y, y], 1), 0.75
def sfx_boom():
    d = 1.6; n = int(d * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 8)) * t) * np.exp(-t * 2.6) 
    return np.stack([y, y], 1)
def sfx_shimmer():
    d = 2.2; n = int(d * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for f, ph in ((1318, 0), (1760, 1), (2637, 2), (3520, 3)): y += np.sin(2 * np.pi * f * t + ph) * (0.6 + 0.4 * np.sin(2 * np.pi * 5 * t + ph))
    y *= np.minimum(1, t / 0.3) * np.exp(-t * 1.6) / 4; return np.stack([y, y * 0.95], 1)

def make_sfx(path):
    total = np.zeros((int(TOTAL * SR) + SR * 2, 2))
    def put(t, snd, g):
        i = max(0, int(t * SR)); seg = snd * db(g); total[i:i + len(seg)] += seg[:len(total) - i]
    # no noise-based sounds (whoosh / reveal swell): Polina disliked the hiss
    put(0.97, sfx_pop(1400, 900, 0.1), -20); put(0.98, sfx_pop(1100, 600, 0.12), -19)
    put(3.12, sfx_pop(900, 300, 0.18), -15)
    for tt in (4.56, 5.04): put(tt, sfx_pop(1000, 600, 0.12), -17)
    for tt in (6.24, 6.96): put(tt + 0.05, sfx_pop(1200, 800, 0.1), -17)
    put(8.1, sfx_pop(1400, 900, 0.1), -20); put(8.45, sfx_pop(1100, 600, 0.12), -19)
    for i in range(5): put(9.27 + i * 0.08, sfx_pop(600, 250, 0.14), -18)
    for tt in (11.15, 11.28, 11.41): put(tt, sfx_tick(), -15); put(tt + 0.01, sfx_pop(1300, 900, 0.08), -20)
    put(14.62, sfx_tick(), -11); put(14.64, sfx_pop(1300, 700, 0.12), -14)
    put(15.95, sfx_boom(), -12); put(16.0, sfx_shimmer(), -24)
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(total, -1, 1) * 32767).astype("<i2").tobytes())

def _frame(i):
    p = f"{TMP}/wr15_{i:04d}.png"; compose(i / FPS).save(p, compress_level=1); return p
def run(out):
    sfx = TMP + "/wr15_sfx.wav"; make_sfx(sfx); n = int(round(TOTAL * FPS))
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/wr15_%04d.png", "-i", AUDIO, "-i", sfx,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[v];[2:a]aresample=44100[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        for tt in sys.argv[3].split(","): compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
