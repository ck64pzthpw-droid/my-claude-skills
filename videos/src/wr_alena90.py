#!/usr/bin/env python3
# ~50 s White Room Group video: Alena (ElevenLabs talking video alena_90dias.mp4) + animated scenes in our style.
# The source has hard jump cuts between takes; each one is hidden under a full-screen panel.
# Usage: wr_alena90.py preview OUT_PREFIX t1,t2,...   |   wr_alena90.py full OUT.mp4
import os, sys, math, subprocess, glob, wave
from multiprocessing import Pool
os.environ.setdefault("SUB_CY", "1660")
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import wr15_luban as L
from wr15_luban import W, H, GOLD, BG, PAPER, SS, CW, CH, CARD_Y, clamp, prog, ease_out, ease_io, lerp, font, with_alpha, ss_canvas, ss_done

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = HERE + "/alena_90dias.mp4"
TMP = L.TMP; FPS = 25
VID_END = 49.64; LOGO_T = 49.9; TOTAL = 52.6
PANEL_H = 1040                      # panel height in split screen
PANEL_SRC_Y = 175                   # scenes are drawn in the 1920 frame; the panel shows rows from here
IMG = L.IMG

# ---------------------------------------------------------------- presenter
# source shots: (start, zoom, focus x, source row that sits at the panel edge in split screen)
SHOTS = [(0.0, 1.0, 0.5, 340), (3.96, 1.0, 0.5, 250), (14.16, 1.0, 0.5, 165), (19.56, 1.0, 0.5, 290),
         (25.64, 1.0, 0.5, 450), (33.56, 1.45, 0.5, 450), (40.16, 1.0, 0.5, 300)]
def shot(t): return [s for s in SHOTS if s[0] <= t][-1]
GIRL = []
def girl_frame(t, split):
    i = min(int(round(t * FPS)), len(GIRL) - 1); g = Image.open(GIRL[i]).convert("RGBA")
    _, z, cx, y0 = shot(t); z = lerp(1.0, z, split)
    if z > 1.001:
        # zoom around her (keeps the row y0 fixed so the split framing stays put)
        cw, ch = W / z, H / z; x0 = clamp(cx * W - cw / 2, 0, W - cw); yy0 = clamp(y0 - y0 / z, 0, H - ch)
        g = g.resize((W, H), Image.LANCZOS, box=(x0, yy0, x0 + cw, yy0 + ch)); y0 = (y0 - yy0) * z
    return g, y0

# panel edge in px over time: 0 = presenter full screen, PANEL_H = split, H = panel covers everything (jump cuts)
EDGE = [(0.0, 0), (0.25, 0), (0.65, 1), (3.55, 1), (3.8, 2), (4.25, 2), (4.7, 0),
        (9.9, 0), (10.35, 1), (13.75, 1), (13.98, 2), (14.4, 2), (14.75, 1),
        (19.15, 1), (19.38, 2), (19.8, 2), (20.15, 1), (25.25, 1), (25.48, 2), (25.98, 2), (26.33, 1),
        (33.15, 1), (33.38, 2), (33.8, 2), (34.15, 1), (39.75, 1), (39.98, 2), (40.45, 2), (40.9, 0),
        (42.2, 0), (42.6, 1), (44.85, 1), (45.15, 2), (99, 2)]
CUTS = [3.96, 14.16, 19.56, 25.64, 33.56, 40.16]
def edge(t):
    v = {0: 0, 1: PANEL_H, 2: H}
    for (a, ka), (b, kb) in zip(EDGE, EDGE[1:]):
        if a <= t <= b: return lerp(v[ka], v[kb], ease_io((t - a) / (b - a)))
    return H

def _grad():
    a = np.zeros((H, 1), np.float32); y = np.arange(H)
    a[:, 0] = np.clip((y - 1380) / 540, 0, 1) ** 1.3 * 0.62 + np.clip((330 - y) / 330, 0, 1) * 0.38
    g = np.zeros((H, W, 4), np.uint8); g[..., 3] = (np.repeat(a, W, 1) * 255).astype(np.uint8); return Image.fromarray(g)
GRAD = _grad()

# ---------------------------------------------------------------- our logo (Polina's final SVG, rendered white)
LOGO = Image.open(HERE + "/refs/wr_logo_white.png").convert("RGBA")
def logo_w(w): return LOGO.resize((w, round(LOGO.height * w / LOGO.width)), Image.LANCZOS)
WM = with_alpha(logo_w(300), 0.92); WM_POS = ((W - WM.width) // 2, 92)
END_LOGO = logo_w(760)

# ---------------------------------------------------------------- subtitles (script spelling, no leading ¿ ¡)
WL = [("Olvídate", 0.00), ("de", .80), ("todo", .96), ("lo", 1.20), ("que", 1.36), ("creías", 1.52), ("saber", 2.08),
      ("sobre", 2.40), ("la", 2.72), ("construcción!", 2.88),
      ("Hola,", 3.84), ("soy", 4.32), ("Alena,", 4.72), ("de", 5.20), ("WhiteRoom", 5.44), ("Group,", 6.08),
      ("y", 6.56), ("hoy", 6.72), ("voy", 7.04), ("a", 7.28), ("cambiar", 7.36), ("por", 7.92), ("completo", 8.08),
      ("tu", 8.56), ("forma", 8.80), ("de", 9.12), ("ver", 9.28), ("las", 9.52), ("casas", 9.76),
      ("Nuestras", 10.40), ("casas", 10.88), ("modulares", 11.20), ("se", 11.84), ("fabrican", 12.00), ("en", 12.56),
      ("fábrica", 12.72), ("con", 13.20), ("precisión", 13.36), ("milimétrica", 13.92), ("y", 14.88), ("llegan", 15.04),
      ("a", 15.44), ("tu", 15.52), ("parcela", 15.76), ("completamente", 16.40), ("terminadas,", 17.12),
      ("listas", 18.08), ("para", 18.56), ("instalar", 18.80),
      ("Sin", 19.52), ("obras", 19.84), ("interminables,", 20.24), ("sin", 21.20), ("escombros", 21.52),
      ("y", 22.24), ("sin", 22.40), ("retrasos", 22.56), ("constantes", 23.28),
      ("En", 24.17), ("solo", 24.49), ("90", 24.81), ("días,", 25.37), ("tendrás", 25.77), ("las", 26.17),
      ("llaves", 26.33), ("de", 26.73), ("tu", 26.89), ("nueva", 27.05), ("casa,", 27.37), ("totalmente", 27.93),
      ("terminada", 28.57), ("y", 29.21), ("lista", 29.45), ("para", 29.77), ("entrar", 30.01), ("a", 30.33), ("vivir", 30.41),
      ("Y", 30.97), ("olvídate", 31.13), ("también", 31.85), ("de", 32.17), ("los", 32.33), ("presupuestos", 32.49),
      ("que", 33.29), ("no", 33.45), ("paran", 33.61), ("de", 34.01), ("subir!", 34.17),
      ("Con", 34.89), ("nosotros,", 35.13), ("el", 35.77), ("precio", 35.93), ("es", 36.41), ("cerrado", 36.57),
      ("Lo", 37.37), ("que", 37.53), ("firmas", 37.69), ("en", 38.17), ("el", 38.25), ("contrato", 38.41),
      ("es", 38.97), ("lo", 39.13), ("que", 39.29), ("pagas", 39.45), ("Ni", 40.09), ("un", 40.33), ("céntimo", 40.57), ("más!", 41.13),
      ("Te", 41.71), ("imaginas", 41.95), ("tener", 42.51), ("tu", 42.83), ("propia", 42.99), ("casa", 43.39),
      ("en", 43.71), ("tan", 43.87), ("solo", 44.11), ("tres", 44.51), ("meses?", 44.83),
      ("Escríbenos", 45.63), ("por", 46.43), ("mensaje", 46.59), ("privado", 46.99),
      ("y", 47.47), ("descubre", 47.63), ("cómo", 48.27), ("hacerlo", 48.51), ("realidad!", 48.99)]
CH_TXT = ["=Olvídate / de todo lo que / creías saber", "sobre la / =construcción!", "Hola, soy / =Alena,",
          "de / =WhiteRoom Group,", "y hoy voy a / =cambiar", "por completo tu / forma de ver / =las casas",
          "Nuestras casas / =modulares", "se fabrican / =en fábrica", "con precisión / =milimétrica",
          "y llegan a / =tu parcela", "=completamente / terminadas,", "listas para / =instalar",
          "Sin obras / =interminables,", "sin / =escombros", "y sin retrasos / =constantes",
          "En solo / =90 días,", "tendrás las / =llaves", "de tu / =nueva casa,", "=totalmente / terminada",
          "y lista para / =entrar a vivir", "Y olvídate también / de los / =presupuestos", "que no paran / =de subir!",
          "Con nosotros, / el precio es / =cerrado", "Lo que firmas / =en el contrato", "es lo que / =pagas",
          "Ni un céntimo / =más!", "Te imaginas / tener tu / =propia casa", "en tan solo / =tres meses?",
          "=Escríbenos / por mensaje privado", "y descubre cómo / hacerlo / =realidad!"]

def build_chunks():
    chunks = []; wi = 0
    for txt in CH_TXT:
        c = L.Chunk(); rows = []
        for ln in txt.split("/"):
            ln = ln.strip(); big = ln.startswith("="); row = []
            for w in ln.lstrip("=").split():
                assert WL[wi][0] == w, (WL[wi], w); row.append(WL[wi]); wi += 1
            rows.append((big, row))
        c.rows = rows; c.start = rows[0][1][0][1] - 0.05; chunks.append(c)
    assert wi == len(WL)
    for a, b in zip(chunks, chunks[1:]): a.end = b.start
    chunks[-1].end = 49.6
    for c in chunks:
        lay = []
        for big, row in c.rows:
            if big:
                s_ = " ".join(w for w, _ in row); size = 108
                while size > 54:
                    f = ImageFont.truetype(L.BIG_FONT, size); tr = -3.0 * size / 112
                    if L.tw(f, s_, tr) <= L.MAXW: break
                    size -= 2
                lay.append((big, row, f, tr, size * 0.98))
            else: lay.append((big, row, L.F_SM, -0.4, 56))
        widths = [L.tw(f, " ".join(w for w, _ in row), tr) for big, row, f, tr, lh in lay]
        x0 = (W - max(widths)) / 2; th = sum(l[4] for l in lay); y = L.SUB_CY - th / 2; items = []
        for big, row, f, tr, lh in lay:
            x = x0; sp = f.getlength(" ") + tr; yoff = -lh * 0.12 if big else 0
            for w, ts in row:
                items.append((w, ts, big, f, tr, x, y + yoff)); x += L.tw(f, w, tr) + sp
            y += lh
        c.items = items
    return chunks
L.CHUNKS = build_chunks()

# ---------------------------------------------------------------- drawing helpers
F_DISP = L.BIG_FONT
def text_img(s, f, fill=(255, 255, 255, 255), tr=0.0):
    w = L.tw(f, s, tr); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(w) + 8, asc + desc + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 4
    for c in s: d.text((x, 4), c, font=f, fill=fill); x += f.getlength(c) + tr
    return im
def paste_c(fr, im, cx, cy, a=1.0, sc=1.0):
    if a <= 0: return
    if sc != 1.0: im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
    fr.alpha_composite(with_alpha(im, a), (int(cx - im.width / 2), int(cy - im.height / 2)))
def label(s, size=34, col=(255, 255, 255, 235)):
    return text_img(s, font("Inter-SemiBold.otf", size), col, 0.3 * size)

def cross_badge(sz, k):
    im, d = ss_canvas(sz, sz); s = SS; c0 = sz / 2 * s; r = sz / 2 * s * (0.7 + 0.3 * ease_out(clamp(k * 2)))
    d.ellipse([c0 - r, c0 - r, c0 + r, c0 + r], fill=GOLD + (255,))
    kk = ease_out(clamp(k * 1.6 - 0.4)); q = 0.2 * sz * s * kk; w = int(sz * 0.1 * s)
    if kk > 0:
        d.line([(c0 - q, c0 - q), (c0 + q, c0 + q)], fill=(20, 20, 22, 255), width=w)
        d.line([(c0 - q, c0 + q), (c0 + q, c0 - q)], fill=(20, 20, 22, 255), width=w)
    return ss_done(im, sz, sz)

def key_icon(sz, col=GOLD):
    """flat key, bow on the left"""
    w, h = sz, int(sz * 0.42); im, d = ss_canvas(w, h); s = SS; cy = h / 2 * s; R = h * 0.46 * s
    d.ellipse([0.04 * h * s, cy - R, 0.04 * h * s + 2 * R, cy + R], fill=col + (255,))
    r2 = R * 0.42; cx2 = 0.04 * h * s + R
    d.ellipse([cx2 - r2, cy - r2, cx2 + r2, cy + r2], fill=(0, 0, 0, 0))
    sh = h * 0.16 * s; x1 = cx2 + R * 0.8; x2 = w * s * 0.97
    d.rectangle([x1, cy - sh / 2, x2, cy + sh / 2], fill=col + (255,))
    for xx, ln in ((0.72, 0.30), (0.84, 0.22)):
        d.rectangle([w * s * xx, cy, w * s * xx + sh * 0.9, cy + h * ln * s], fill=col + (255,))
    return ss_done(im, w, h)

def lock_icon(sz, col=GOLD, dark=(20, 20, 22)):
    im, d = ss_canvas(sz, sz); s = SS; u = sz * s
    d.arc([0.25 * u, 0.06 * u, 0.75 * u, 0.6 * u], 180, 360, fill=col + (255,), width=int(0.09 * u))
    d.line([(0.295 * u, 0.33 * u), (0.295 * u, 0.48 * u)], fill=col + (255,), width=int(0.09 * u))
    d.line([(0.705 * u, 0.33 * u), (0.705 * u, 0.48 * u)], fill=col + (255,), width=int(0.09 * u))
    d.rounded_rectangle([0.15 * u, 0.44 * u, 0.85 * u, 0.94 * u], 0.08 * u, fill=col + (255,))
    d.ellipse([0.44 * u, 0.6 * u, 0.56 * u, 0.72 * u], fill=dark + (255,))
    d.rectangle([0.475 * u, 0.68 * u, 0.525 * u, 0.82 * u], fill=dark + (255,))
    return ss_done(im, sz, sz)

def polyline_part(pts, k):
    """first fraction k (by length) of a polyline"""
    if k <= 0: return pts[:1]
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; tot = sum(seg) * k; out = [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), seg):
        if tot >= l: out.append(b); tot -= l
        else: out.append((lerp(a[0], b[0], tot / l), lerp(a[1], b[1], tot / l))); break
    return out

def chip_at(fr, txt, k, cy, icon="dot"):
    r = L.chip(txt, k, cy, icon)
    if r: fr.alpha_composite(*r)

def card_photo(img, z, cx=0.5, cy=0.5): return L.card_of(img, z, cx, cy)

# ---------------------------------------------------------------- assets
FACTORY = L.cover(IMG + "/factory.jpg", CW * 2, CH * 2, 0.5, 0.5)
STEEL = L.FRAME
PLOT = L.cover(IMG + "/v-plot.jpg", CW * 2, CH * 2, 0.55, 0.6)
LIVING = L.LIVING
HOUSE = L.END1

# ---------------------------------------------------------------- scenes (drawn in 1920-high space; panel = rows from PANEL_SRC_Y)
CY = CARD_Y                                      # card centre (shows ~685 px down the panel)

def sc_hook(t):                                  # sketch -> real S70, push-in
    tt = max(0.0, t - 0.3)
    return L.sc_hook_at(min(tt, 3.6), pin=0)

def dim_line(fr, x0, y0, x1, y1, k, txt, ka):
    """gold dimension line with end ticks and a label, drawn to fraction k"""
    if k <= 0: return
    im, d = ss_canvas(W, H); s = SS; xe, ye = lerp(x0, x1, k), lerp(y0, y1, k)
    d.line([(x0 * s, y0 * s), (xe * s, ye * s)], fill=GOLD + (255,), width=5 * s)
    vert = abs(x1 - x0) < abs(y1 - y0)
    for (xx, yy) in ((x0, y0),) + (((x1, y1),) if k >= 1 else ()):
        if vert: d.line([((xx - 22) * s, yy * s), ((xx + 22) * s, yy * s)], fill=GOLD + (255,), width=5 * s)
        else: d.line([(xx * s, (yy - 22) * s), (xx * s, (yy + 22) * s)], fill=GOLD + (255,), width=5 * s)
    fr.alpha_composite(ss_done(im, W, H))
    if ka > 0:
        f = font("Inter-Bold.otf", 40); tx = text_img(txt, f, (20, 20, 22, 255))
        pw, ph = tx.width + 36, tx.height + 10; pill, dd = ss_canvas(pw, ph)
        dd.rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], ph * SS / 2, fill=GOLD + (255,)); pill = ss_done(pill, pw, ph)
        pill.alpha_composite(tx, (18, 3))
        paste_c(fr, pill, (x0 + x1) / 2, (y0 + y1) / 2, ease_out(ka), 0.85 + 0.15 * ease_out(ka))

def sc_factory(t):                               # 9.8 - 14.7 "se fabrican en fábrica con precisión milimétrica"
    fr = L.BGI.copy()
    z = 1.04 + 0.08 * prog(t, 9.8, 3.0)
    c = card_photo(FACTORY, z, 0.5, 0.5)
    kw = ease_io(prog(t, 12.5, 0.7))
    if kw > 0: c = L.wipe(c, card_photo(STEEL, 1.02 + 0.06 * prog(t, 12.5, 2.5), 0.45, 0.6), kw * (CW + 80), 80, line=kw < 1)
    kin = ease_out(prog(t, 9.8, 0.5)); L.put_card(fr, c, CY, 0.94 + 0.06 * kin, kin)
    chip_at(fr, "FÁBRICA", prog(t, 12.0, 0.4) * (1 - ease_io(prog(t, 12.6, 0.3))), CY - CH / 2 - 70)
    # dimensions on "precisión milimétrica": real S70 length / height
    x0, x1 = (W - CW) / 2 + 70, (W + CW) / 2 - 70; yb = CY + CH / 2 - 70
    kd = ease_io(prog(t, 13.3, 0.8)); n = int(round(11400 * kd / 10)) * 10
    dim_line(fr, x0, yb, x1, yb, kd, f"{n:,} mm".replace(",", " "), prog(t, 13.4, 0.3))
    kv = ease_io(prog(t, 13.75, 0.6)); yt = CY - CH / 2 + 60; xr = x1 + 10
    m = int(round(3300 * kv / 10)) * 10
    dim_line(fr, xr, yb - 50, xr, yt, kv, f"{m:,} mm".replace(",", " "), prog(t, 13.85, 0.3))
    return fr

ROUTE = [(210, 560), (420, 520), (620, 760), (560, 940), (720, 1110), (860, 1140)]
def bez(pts, n=80):                              # smooth path through points (Catmull-Rom)
    out = []; P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(n // (len(pts) - 1)):
            u = j / (n // (len(pts) - 1)); u2, u3 = u * u, u * u * u
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in (0, 1)))
    return out + [pts[-1]]
PATH = bez(ROUTE, 200)
def sc_route(t):                                 # 14.7 - 19.3 "llegan a tu parcela completamente terminadas"
    fr = L.BGI.copy()
    k_map = 1 - ease_io(prog(t, 16.25, 0.4))
    if k_map > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        im, d = ss_canvas(W, H); s = SS
        kl = ease_io(prog(t, 14.75, 0.7)); part = polyline_part(PATH, kl)
        # dashed route
        acc = 0
        for a, b in zip(part, part[1:]):
            l = math.dist(a, b); on = (acc // 22) % 2 == 0; acc += l
            if on: d.line([(a[0] * s, a[1] * s), (b[0] * s, b[1] * s)], fill=GOLD + (230,), width=6 * s)
        sx, sy = ROUTE[0]; r0 = 18 * ease_out(prog(t, 14.7, 0.3))
        d.ellipse([(sx - r0) * s, (sy - r0) * s, (sx + r0) * s, (sy + r0) * s], fill=(255, 255, 255, 255))
        lay.alpha_composite(ss_done(im, W, H))
        paste_c(lay, label("FÁBRICA", 34), sx + 10, sy - 60, ease_out(prog(t, 14.8, 0.3)))
        # destination pin
        kp = prog(t, 15.7, 0.35)
        if kp > 0:
            ex, ey = ROUTE[-1]; bounce = math.sin(math.pi * kp) * 30
            pin, dd = ss_canvas(90, 120); u = SS
            dd.ellipse([10 * u, 4 * u, 80 * u, 74 * u], fill=GOLD + (255,))
            dd.polygon([(16 * u, 54 * u), (74 * u, 54 * u), (45 * u, 116 * u)], fill=GOLD + (255,))
            dd.ellipse([30 * u, 24 * u, 60 * u, 54 * u], fill=BG + (255,))
            lay.alpha_composite(ss_done(pin, 90, 120), (int(ex - 45), int(ey - 116 - bounce)))
            paste_c(lay, label("TU PARCELA", 34), ex - 60, ey + 50, ease_out(kp))
        # the module travelling along the route
        km = ease_io(prog(t, 14.95, 1.2))
        if km > 0:
            i = min(len(PATH) - 1, int(km * (len(PATH) - 1))); x, y = PATH[i]
            mod, dd = ss_canvas(150, 64); u = SS
            dd.rounded_rectangle([0, 0, 150 * u - 1, 64 * u - 1], 30 * u, fill=(250, 250, 250, 255))
            dd.rounded_rectangle([22 * u, 16 * u, 128 * u, 40 * u], 10 * u, fill=(40, 44, 52, 255))
            fr_m = ss_done(mod, 150, 64); sh, pad = L.shadow_of(fr_m, 12, 0.5)
            lay.alpha_composite(sh, (int(x - 75 - pad), int(y - 70 - pad + 10))); lay.alpha_composite(fr_m, (int(x - 75), int(y - 70)))
        fr.alpha_composite(with_alpha(lay, k_map))
    kc = ease_out(prog(t, 16.3, 0.5))
    if kc > 0:
        c = card_photo(PLOT, 1.02 + 0.08 * prog(t, 16.3, 3.0), 0.55, 0.6)
        L.put_card(fr, c, CY, 0.92 + 0.08 * kc, kc)
        chip_at(fr, "TERMINADA", prog(t, 17.1, 0.4) * (1 - ease_io(prog(t, 17.9, 0.25))), CY - CH / 2 - 70)
        chip_at(fr, "LISTA PARA INSTALAR", prog(t, 18.1, 0.4), CY - CH / 2 - 70)
        kb = prog(t, 18.75, 0.5)
        if kb > 0: fr.alpha_composite(L.check_badge(110, kb), (int((W + CW) / 2 - 140), int(CY + CH / 2 - 140)))
    return fr

SIN = [("Obras interminables", 19.1, 20.4), ("Escombros", 21.2, 21.8), ("Retrasos constantes", 22.4, 23.1)]
F_SIN = ImageFont.truetype(F_DISP, 66)
def sc_sin(t):                                   # 19.3 - 24.1 "sin obras, sin escombros, sin retrasos"
    fr = L.BGI.copy()
    for i, (txt, t0, ts) in enumerate(SIN):
        k = ease_out(prog(t, t0, 0.4))
        if k <= 0: continue
        y = CY - 220 + i * 220; x0 = 120
        row, d = ss_canvas(W - 2 * 90, 170); s = SS
        d.rounded_rectangle([0, 0, (W - 180) * s - 1, 170 * s - 1], 40 * s, fill=(255, 255, 255, 14), outline=(255, 255, 255, 40), width=2 * s)
        fr.alpha_composite(with_alpha(ss_done(row, W - 180, 170), k), (90, int(y - 85 + (1 - k) * 30)))
        kx = prog(t, ts - 0.15, 0.45)
        b = cross_badge(100, kx) if kx > 0 else None
        if b: fr.alpha_composite(b, (x0 + 10, int(y - 50 + (1 - k) * 30)))
        ks = ease_io(prog(t, ts, 0.4)); g = int(lerp(255, 120, ks))
        tx = text_img(txt, F_SIN, (g, g, g, 255), -1.5)
        fr.alpha_composite(with_alpha(tx, k), (x0 + 140, int(y - tx.height / 2 - 6 + (1 - k) * 30)))
        if ks > 0:
            im, d = ss_canvas(W, 10)
            d.line([((x0 + 140) * s, 5 * s), ((x0 + 140 + (tx.width - 4) * ks) * s, 5 * s)], fill=GOLD + (255,), width=6 * s)
            fr.alpha_composite(ss_done(im, W, 10), (0, int(y - 5 + (1 - k) * 30)))
    return fr

F_NUM = ImageFont.truetype(F_DISP, 300)
def sc_90(t):                                    # 24.1 - 30.95 "en solo 90 días tendrás las llaves ... lista para vivir"
    fr = L.BGI.copy(); cx, cy = W / 2, CY
    k_out = ease_io(prog(t, 26.15, 0.35))
    if k_out < 1:
        a = 1 - k_out; sc = 1 - 0.15 * k_out
        kr = ease_io(prog(t, 24.3, 1.35)); n = int(round(90 * kr))
        im, d = ss_canvas(W, H); s = SS; R = 330
        d.ellipse([(cx - R) * s, (cy - R) * s, (cx + R) * s, (cy + R) * s], outline=(255, 255, 255, 40), width=14 * s)
        if kr > 0: d.arc([(cx - R) * s, (cy - R) * s, (cx + R) * s, (cy + R) * s], -90, -90 + 360 * kr, fill=GOLD + (255,), width=14 * s)
        ring = ss_done(im, W, H)
        if sc != 1: ring = L.zoom(ring, 1 / sc) if sc > 1 else ring.resize((round(W * sc), round(H * sc)), Image.LANCZOS)
        fr.alpha_composite(with_alpha(ring, a * ease_out(prog(t, 24.15, 0.3))), (int((W - ring.width) / 2), int((H - ring.height) / 2 + (1 - sc) * (cy - H / 2))))
        kin = ease_out(prog(t, 24.2, 0.3))
        paste_c(fr, text_img(str(n), F_NUM, (255, 255, 255, 255), -8), cx, cy - 40, a * kin, sc)
        paste_c(fr, label("DÍAS", 44, GOLD + (255,)), cx, cy + 140 * sc, a * ease_out(prog(t, 25.3, 0.3)), sc)
    # the keys
    kk = ease_out(prog(t, 26.25, 0.5)); k_gone = ease_io(prog(t, 27.6, 0.35))
    if kk > 0 and k_gone < 1:
        key = key_icon(520).rotate(lerp(-35, 0, kk), resample=Image.BICUBIC, expand=True)
        paste_c(fr, key, cx, cy - 10, kk * (1 - k_gone), 0.8 + 0.2 * kk)
        paste_c(fr, label("TUS LLAVES", 40), cx, cy + 210, ease_out(prog(t, 26.5, 0.3)) * (1 - k_gone))
    kc = ease_out(prog(t, 27.7, 0.5))
    if kc > 0:
        c = card_photo(LIVING, 1.02 + 0.08 * prog(t, 27.7, 3.3), 0.5, 0.55)
        L.put_card(fr, c, CY, 0.92 + 0.08 * kc, kc)
        chip_at(fr, "LISTA PARA VIVIR", prog(t, 29.4, 0.4), CY - CH / 2 - 70)
    return fr

CHART = [(0, .12), (.12, .16), (.25, .22), (.37, .27), (.5, .38), (.62, .45), (.75, .6), (.87, .72), (1, .9)]
def sc_price(t):                                 # 30.95 - 37.3 rising budget, then the price locked flat
    fr = L.BGI.copy()
    kin = ease_out(prog(t, 30.95, 0.45))
    bw, bh = 940, 640; bx, by = (W - bw) / 2, CY - bh / 2
    im, d = ss_canvas(W, H); s = SS
    d.rounded_rectangle([bx * s, by * s, (bx + bw) * s, (by + bh) * s], 34 * s, fill=(30, 30, 35, 255), outline=(255, 255, 255, 30), width=2 * s)
    gx0, gx1, gy0, gy1 = bx + 110, bx + bw - 80, by + bh - 90, by + 80
    for i in range(5):
        yy = lerp(gy0, gy1, i / 4); d.line([(gx0 * s, yy * s), (gx1 * s, yy * s)], fill=(255, 255, 255, 22), width=2 * s)
    d.line([(gx0 * s, gy0 * s), (gx1 * s, gy0 * s)], fill=(255, 255, 255, 90), width=3 * s)
    P = [(lerp(gx0, gx1, x), lerp(gy0, gy1, y)) for x, y in CHART]
    kr = ease_io(prog(t, 31.4, 2.6)); fade = 1 - 0.7 * ease_io(prog(t, 35.0, 0.5))
    red = (226, 92, 80)
    if kr > 0:
        part = polyline_part(P, kr)
        d.line([(x * s, y * s) for x, y in part], fill=red + (int(255 * fade),), width=8 * s, joint="curve")
        ex, ey = part[-1]; r = 13
        d.ellipse([(ex - r) * s, (ey - r) * s, (ex + r) * s, (ey + r) * s], fill=red + (int(255 * fade),))
    kf = ease_io(prog(t, 35.0, 0.9)); yf = P[0][1]
    if kf > 0:
        d.line([(gx0 * s, yf * s), (lerp(gx0, gx1, kf) * s, yf * s)], fill=GOLD + (255,), width=10 * s)
    card = ss_done(im, W, H); fr.alpha_composite(with_alpha(card, kin))
    paste_c(fr, label("€", 44, (255, 255, 255, 170)), bx + 60, gy1 + 10, kin)
    paste_c(fr, label("PRESUPUESTO", 26, (255, 255, 255, 150)), bx + 245, by + 45, kin * (1 - ease_io(prog(t, 35.0, 0.4))))
    if kr > 0:
        pct = int(round(40 * kr)); ex, ey = polyline_part(P, kr)[-1]
        paste_c(fr, text_img(f"+{pct}%", font("Inter-Bold.otf", 52), red + (255,)), min(ex, gx1 - 60) - 30, ey - 60, ease_out(prog(t, 31.6, 0.3)) * fade)
    kl = prog(t, 36.3, 0.45)
    if kl > 0:
        paste_c(fr, lock_icon(130), gx1 - 10, yf - 90, ease_out(kl), 0.6 + 0.4 * ease_out(kl))
        paste_c(fr, label("PRECIO CERRADO", 34, GOLD + (255,)), (gx0 + gx1) / 2 - 70, yf - 60, ease_out(prog(t, 36.55, 0.35)))
    return fr

SCRIBBLE = [(0, .6), (.06, .1), (.12, .8), (.18, .3), (.22, .55), (.3, .15), (.34, .7), (.42, .4), (.5, .6),
            (.56, .2), (.62, .75), (.7, .45), (.8, .5), (1, .35)]
def sc_contract(t):                              # 37.3 - 41.0 "lo que firmas en el contrato es lo que pagas, ni un céntimo más"
    fr = L.BGI.copy(); kin = ease_out(prog(t, 37.3, 0.45))
    pw, ph = 560, 700; px, py = (W - pw) / 2, CY - ph / 2 + (1 - kin) * 40
    paper, d = ss_canvas(pw, ph); s = SS
    d.rounded_rectangle([0, 0, pw * s - 1, ph * s - 1], 26 * s, fill=PAPER + (255,))
    for i, wl in enumerate((0.9, 0.75, 0.85, 0.6, 0.8)):
        y = 170 + i * 46; d.rounded_rectangle([60 * s, y * s, (60 + (pw - 120) * wl) * s, (y + 16) * s], 8 * s, fill=(200, 198, 192, 255))
    d.rounded_rectangle([60 * s, 420 * s, (pw - 60) * s, 500 * s], 16 * s, fill=(236, 232, 222, 255))
    d.line([(60 * s, 610 * s), (pw * 0.62 * s, 610 * s)], fill=(150, 148, 142, 255), width=3 * s)
    ks = ease_io(prog(t, 37.65, 0.8))
    if ks > 0:
        sp = [(80 + x * 230, 520 + y * 80) for x, y in SCRIBBLE]
        d.line([(x * s, y * s) for x, y in polyline_part(sp, ks)], fill=(30, 44, 96, 255), width=5 * s, joint="curve")
    pap = ss_done(paper, pw, ph); dd = ImageDraw.Draw(pap)
    dd.text((60, 70), "CONTRATO", font=font("Inter-Bold.otf", 46), fill=(24, 24, 26, 255))
    dd.text((84, 440), "PRECIO TOTAL", font=font("Inter-SemiBold.otf", 28), fill=(90, 88, 84, 255))
    dd.text((pw - 84 - font("Inter-Bold.otf", 30).getlength("FIJO"), 438), "FIJO", font=font("Inter-Bold.otf", 30), fill=(170, 120, 60, 255))
    sh, pad = L.shadow_of(pap, 24, 0.55 * kin)
    fr.alpha_composite(sh, (int(px - pad), int(py - pad + 18))); fr.alpha_composite(with_alpha(pap, kin), (int(px), int(py)))
    # stamp on "pagas"
    kp = prog(t, 39.4, 0.3)
    if kp > 0:
        f = font("Inter-Bold.otf", 40); tx = text_img("PRECIO CERRADO", f, GOLD + (255,), 3)
        sw, sh_ = tx.width + 60, tx.height + 40; st, d = ss_canvas(sw, sh_)
        d.rounded_rectangle([4 * SS, 4 * SS, (sw - 4) * SS, (sh_ - 4) * SS], 18 * SS, outline=GOLD + (255,), width=6 * SS)
        st = ss_done(st, sw, sh_); st.alpha_composite(tx, (30, 20)); st = st.rotate(12, resample=Image.BICUBIC, expand=True)
        paste_c(fr, st, W / 2 + 40, py + 330, ease_out(kp), 1.4 - 0.4 * ease_out(kp))
    # "+0 €" badge on "ni un céntimo más"
    kb = prog(t, 40.05, 0.35)
    if kb > 0:
        bs = 220; b, d = ss_canvas(bs, bs); d.ellipse([0, 0, bs * SS - 1, bs * SS - 1], fill=GOLD + (255,)); b = ss_done(b, bs, bs)
        tx = text_img("+0 €", ImageFont.truetype(F_DISP, 76), (20, 20, 22, 255), -2); b.alpha_composite(tx, ((bs - tx.width) // 2, (bs - tx.height) // 2 - 6))
        sc = 0.6 + 0.4 * ease_out(kb) + 0.08 * math.sin(math.pi * clamp(kb * 1.4))
        paste_c(fr, b, px + pw - 20, py + 30, ease_out(kb), sc)
    return fr

def sc_3m(t):                                    # 41.0 - 45.2 "te imaginas tener tu propia casa en tan solo tres meses?"
    fr = L.BGI.copy(); kin = ease_out(prog(t, 42.2, 0.5))
    c = card_photo(HOUSE, 1.02 + 0.1 * prog(t, 42.2, 3.0), 0.5, 0.7)
    L.put_card(fr, c, CY, 0.92 + 0.08 * kin, kin)
    chip_at(fr, "TU PROPIA CASA", prog(t, 42.95, 0.4) * (1 - ease_io(prog(t, 44.25, 0.25))), CY - CH / 2 - 70)
    k3 = prog(t, 44.45, 0.4)
    if k3 > 0:
        b, d = ss_canvas(420, 130)
        d.rounded_rectangle([0, 0, 420 * SS - 1, 130 * SS - 1], 65 * SS, fill=GOLD + (255,)); b = ss_done(b, 420, 130)
        tx = text_img("3 MESES", ImageFont.truetype(F_DISP, 72), (20, 20, 22, 255), -1); b.alpha_composite(tx, ((420 - tx.width) // 2, (130 - tx.height) // 2 - 6))
        paste_c(fr, b, W / 2, CY - CH / 2 - 40, ease_out(k3), 0.8 + 0.2 * ease_out(k3))
    return fr

CTA_T0 = 45.35 - 14.3                             # draw_cta's own timing starts at 14.3
def sc_cta(t): return L.draw_cta(L.BGI.copy(), t, H // 2 + PANEL_SRC_Y, CTA_T0)

SCENES = [(0.0, 4.6, sc_hook), (9.7, 14.7, sc_factory), (14.7, 19.3, sc_route), (19.3, 24.1, sc_sin),
          (24.1, 30.95, sc_90), (30.95, 37.3, sc_price), (37.3, 41.0, sc_contract), (41.0, 45.2, sc_3m), (45.2, 99, sc_cta)]
XF = 0.3
def panel(t):
    fr = None
    for i, (a, b, fn) in enumerate(SCENES):
        if a - (XF if i else 0) <= t < b:
            img = fn(t); fr = img if fr is None else Image.blend(fr, img, ease_io(prog(t, a - XF, XF)))
    if fr is None: fr = L.BGI.copy()
    return fr.crop((0, PANEL_SRC_Y, W, PANEL_SRC_Y + H))

def compose(t):
    if t >= VID_END: fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        e = edge(t); split = clamp(e / PANEL_H)
        fr = Image.new("RGBA", (W, H), BG + (255,))
        if e < H:
            g, y0 = girl_frame(t, split); dy = int((PANEL_H - y0) * split + max(0, e - PANEL_H))
            fr.alpha_composite(g, (0, dy))
        ye = int(round(e))
        if ye > 0:
            pf = panel(t); bg = Image.new("RGBA", pf.size, BG + (255,)); bg.alpha_composite(pf)
            p = bg.crop((0, PANEL_H - ye, W, PANEL_H)) if ye <= PANEL_H else bg.crop((0, 0, W, ye))
            fr.alpha_composite(p, (0, 0))
            if ye < H:
                line = Image.new("RGBA", (W, 4), GOLD + (200,)); fr.alpha_composite(line, (0, max(0, ye - 2)))
        fr.alpha_composite(GRAD)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ov.alpha_composite(WM, WM_POS)
        if 4.5 <= t <= 9.9:                       # lower third while she introduces herself
            r = L.chip("ALENA · WHITEROOM GROUP", prog(t, 4.75, 0.45) * (1 - ease_io(prog(t, 9.2, 0.35))), 1440, "dot")
            if r: ov.alpha_composite(*r)
        L.draw_subs(ov, t); fr.alpha_composite(ov)
    FB0 = LOGO_T - 0.45
    if t >= FB0:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), ease_io(prog(t, FB0, 0.45)))
        lk = ease_out(prog(t, LOGO_T, 1.0)) * (1 - ease_io(prog(t, TOTAL - 0.7, 0.6)))
        if lk > 0:
            sc = 0.97 + 0.03 * ease_out(prog(t, LOGO_T, 1.4))
            lg = END_LOGO.resize((round(END_LOGO.width * sc), round(END_LOGO.height * sc)), Image.LANCZOS)
            fr.alpha_composite(with_alpha(lg, lk), ((W - lg.width) // 2, (H - lg.height) // 2 - 20))
    return fr.convert("RGB")

# ---------------------------------------------------------------- sound: soft pops only (no hiss), boom on the logo
def make_sfx(path):
    SR = L.SR; total = np.zeros((int(TOTAL * SR) + SR * 2, 2))
    def put(t, snd, g):
        i = max(0, int(t * SR)); seg = snd * L.db(g); total[i:i + len(seg)] += seg[:len(total) - i]
    pop = L.sfx_pop
    for tt in (0.95, 4.75, 12.0, 15.7, 17.1, 18.1, 29.4, 36.55, 42.95): put(tt, pop(1200, 800, 0.1), -20)
    for tt in (13.4, 13.85, 18.75): put(tt, L.sfx_tick(), -17)
    for _, _, ts in SIN: put(ts - 0.1, pop(900, 400, 0.14), -17)
    put(25.6, pop(1400, 900, 0.1), -17); put(26.3, L.sfx_tick(), -16)
    put(36.3, L.sfx_tick(), -15); put(39.4, pop(700, 250, 0.18), -14); put(40.05, pop(1300, 800, 0.12), -16)
    put(44.45, pop(1200, 700, 0.12), -16)
    put(CTA_T0 + 14.62, L.sfx_tick(), -12); put(CTA_T0 + 14.64, pop(1300, 700, 0.12), -15)
    put(LOGO_T, L.sfx_boom(), -12); put(LOGO_T + 0.05, L.sfx_shimmer(), -24)
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(total, -1, 1) * 32767).astype("<i2").tobytes())

def extract():
    d = TMP + "/a90_frames"; os.makedirs(d, exist_ok=True)
    if not glob.glob(d + "/*.png"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-vf", f"fps={FPS},scale={W}:{H}", d + "/g_%04d.png"], check=True)
    GIRL[:] = sorted(glob.glob(d + "/*.png"))
def _frame(i):
    if not GIRL: extract()
    p = f"{TMP}/a90_{i:04d}.png"; compose(i / FPS).save(p, compress_level=1); return p
def run(out):
    extract(); sfx = TMP + "/a90_sfx.wav"; make_sfx(sfx); n = int(round(TOTAL * FPS))
    import music; mus = TMP + "/a90_music.wav"; music.write(mus, TOTAL, LOGO_T)
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/a90_%04d.png", "-i", SRC, "-i", sfx, "-i", mus,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad,asplit=2[v][vk];[2:a]aresample=44100[s];"
        "[3:a]aresample=44100,volume=-22dB[m0];[m0][vk]sidechaincompress=threshold=0.02:ratio=3:attack=30:release=400[m];"
        "[v][s][m]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        extract()
        for tt in sys.argv[3].split(","): compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
