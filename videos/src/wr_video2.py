#!/usr/bin/env python3
# Video 2 «Casas amplias + domótica»: Alena (lip-sync video video2_src.mp4, 30 fps) + scenes in style v2.
# Same engine and rules as Video 1 (wr_alena90s.py): jump cuts under a full-screen panel, Montserrat subtitles,
# dark lower third, CTA button on the panel seam at the screen centre, no music, no repeated pops.
# Usage: wr_video2.py preview OUT_PREFIX t1,t2,...   |   wr_video2.py full OUT.mp4
import os, sys, math, subprocess, glob, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw
import wr15_luban as L
import wr_alena90s as V
import wr_alena90 as A
import wr_style as S
from wr_style import MF, text, put, eyebrow, pill, hair, glow, INK
from wr15_luban import W, H, GOLD, SS, clamp, prog, ease_out, ease_io, lerp, with_alpha, ss_canvas, ss_done

HERE = V.HERE; TMP = V.TMP
A.SRC = HERE + "/video2_src.mp4"; A.FPS = FPS = 30
V.VID_END = VID_END = 52.93; V.LOGO_T = LOGO_T = 53.15; V.TOTAL = TOTAL = 55.9
V.LT = (5.75, 7.45); V.CTA_T = CTA_T = 47.7
X0, EY, CYP = V.X0, V.EY, V.CYP

# ---------------------------------------------------------------- presenter: shots, cuts, framing
# hard cuts in the source: 9.70 15.53 24.90 30.73 41.30 43.97 (frame-difference scan)
# (start, zoom in split, focus x, source row at the panel edge); wide shots are zoomed so she reads at the same size
A.SHOTS[:] = [(0.0, 1.35, 0.5, 420), (9.70, 1.0, 0.5, 320), (15.53, 1.6, 0.5, 550), (24.90, 1.0, 0.5, 310),
              (30.73, 1.35, 0.5, 435), (41.30, 1.0, 0.5, 310), (43.97, 1.35, 0.5, 450)]
A.EDGE[:] = [(0.0, 0), (0.25, 0), (0.65, 1), (5.2, 1), (5.55, 0), (7.7, 0), (8.15, 2),
             (9.95, 2), (10.4, 1), (15.1, 1), (15.48, 2), (25.2, 2), (25.6, 1), (30.45, 1), (30.66, 2), (31.05, 2), (31.4, 1),
             (41.0, 1), (41.23, 2), (41.6, 2), (41.95, 1), (43.65, 1), (43.9, 2), (44.3, 2), (44.65, 1),
             (52.3, 1), (52.65, 2), (99, 2)]

# ---------------------------------------------------------------- words (parakeet timings, script spelling)
A.WL[:] = [("Eso", 0.00), ("de", .40), ("que", .48), ("una", .64), ("casa", .88), ("modular", 1.12), ("es", 1.76), ("una", 1.92),
    ("caja", 2.08), ("pequeña", 2.48), ("y", 2.96), ("estrecha", 3.12), ("ya", 3.84), ("es", 4.08), ("cosa", 4.32), ("del", 4.64),
    ("pasado", 4.88), ("Soy", 5.60), ("Alena,", 5.92), ("de", 6.48), ("WhiteRoom", 6.72), ("Group,", 7.36), ("y", 7.84),
    ("nosotros", 8.00), ("construimos", 8.56), ("casas", 9.20), ("amplias", 9.60), ("de", 10.08), ("100", 10.24), ("e", 10.72),
    ("incluso", 10.88), ("200", 11.44), ("metros", 12.24), ("cuadrados", 12.64),
    ("Pero", 13.56), ("lo", 13.88), ("que", 13.96), ("de", 14.12), ("verdad", 14.28), ("te", 14.60), ("va", 14.76), ("a", 14.92),
    ("sorprender", 15.00), ("está", 15.72), ("en", 16.04), ("el", 16.20), ("interior", 16.36),
    ("Todas", 17.08), ("nuestras", 17.48), ("casas", 17.88), ("incluyen", 18.28), ("un", 18.84), ("sistema", 19.00),
    ("domótico", 19.40), ("premium,", 20.12), ("sin", 20.76), ("ningún", 21.00), ("coste", 21.40), ("adicional", 21.88),
    ("Olvídate", 22.68), ("de", 23.40), ("las", 23.56), ("llaves", 23.72), ("La", 24.36), ("puerta", 24.52), ("se", 24.92),
    ("abre", 25.08), ("con", 25.48), ("un", 25.64), ("solo", 25.80), ("toque", 26.12),
    ("Y", 26.77), ("una", 26.93), ("vez", 27.17), ("dentro,", 27.41), ("puedes", 27.97), ("controlar", 28.29), ("toda", 28.85),
    ("tu", 29.17), ("casa", 29.33), ("como", 29.65), ("si", 29.89), ("estuvieras", 30.05), ("en", 30.69), ("una", 30.85),
    ("película", 31.01), ("de", 31.49), ("ciencia", 31.57), ("ficción", 32.05),
    ("Las", 32.85), ("luces,", 33.09), ("la", 33.73), ("temperatura,", 33.89), ("las", 34.69), ("persianas", 34.93),
    ("e", 35.81), ("incluso", 35.97), ("una", 36.45), ("pantalla", 36.69), ("retráctil", 37.09), ("oculta", 37.89),
    ("Todo", 38.53), ("responde", 38.85), ("a", 39.33), ("tus", 39.41), ("órdenes", 39.65), ("de", 39.97), ("voz", 40.13),
    ("Y", 40.68), ("lo", 40.92), ("mejor", 41.08), ("de", 41.32), ("todo,", 41.48), ("no", 42.04), ("es", 42.20), ("un", 42.36),
    ("lujo", 42.52), ("exclusivo", 42.92), ("que", 43.40), ("cuesta", 43.56), ("una", 43.96), ("fortuna", 44.20),
    ("Es", 44.84), ("nuestro", 45.08), ("estándar,", 45.40), ("incluido", 46.12), ("en", 46.68), ("el", 46.84), ("precio", 46.92),
    ("Escríbenos", 47.64), ("por", 48.36), ("mensaje", 48.52), ("privado", 48.92), ("y", 49.32), ("cuéntanos,", 49.48),
    ("cómo", 50.20), ("sería", 50.52), ("la", 50.92), ("casa", 51.08), ("del", 51.40), ("futuro", 51.56), ("de", 51.96),
    ("tus", 52.04), ("sueños?", 52.28)]
A.CH_TXT[:] = ["Eso de que una casa / =modular", "es una caja / =pequeña y estrecha", "ya es / =cosa del pasado",
    "Soy / =Alena,", "de / =WhiteRoom Group,", "y nosotros / =construimos", "=casas amplias",
    "de 100 e incluso / =200 metros cuadrados", "Pero lo que de verdad / te va a / =sorprender", "está en / =el interior",
    "Todas nuestras casas / =incluyen", "un sistema / =domótico premium,", "sin ningún / =coste adicional",
    "=Olvídate / de las llaves", "La puerta se abre / con un solo / =toque", "Y una vez dentro, / =puedes controlar",
    "toda tu casa / =como si estuvieras", "en una película / =de ciencia ficción", "Las / =luces,", "la / =temperatura,",
    "las / =persianas", "e incluso una / =pantalla retráctil / oculta", "Todo responde / a tus / =órdenes de voz",
    "Y lo mejor / =de todo,", "no es un / =lujo exclusivo", "que cuesta / =una fortuna", "Es nuestro / =estándar,",
    "=incluido / en el precio", "=Escríbenos / por mensaje privado", "y cuéntanos, / cómo sería la casa / =del futuro",
    "de tus / =sueños?"]
L.CHUNKS = V.build_chunks(); L.CHUNKS[-1].end = VID_END

def DY(t):
    e = A.edge(t); e = e * V.PANEL_H / A.PANEL_H if e <= A.PANEL_H else lerp(V.PANEL_H, H, (e - A.PANEL_H) / (H - A.PANEL_H))
    return clamp((e - V.PANEL_H) / (H - V.PANEL_H)) * (H / 2 - CYP - 40)

# voice envelope (drives the voice-control waveform)
def _env():
    p = TMP + "/v2.wav"
    if not os.path.exists(p): subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.SRC, "-ac", "1", "-ar", "16000", p], check=True)
    w = wave.open(p); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n = 320; e = np.sqrt(np.convolve(a * a, np.ones(n) / n, "same"))[::160]      # 100 values / s
    return e / (np.percentile(e, 98) + 1e-6)
ENV = _env()
def vo(t): i = int(t * 100); return float(ENV[min(max(i, 0), len(ENV) - 1)])

# ---------------------------------------------------------------- small pieces
def node(label, w=250, h=78, on=1.0, focus=False):
    im, d = ss_canvas(w, h)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], 20 * SS, fill=(26, 26, 30, 245),
                        outline=(GOLD if focus else (255, 255, 255)) + (int((230 if focus else 60) * on),), width=2 * SS)
    im = ss_done(im, w, h); t_ = text(label.upper(), MF(600, 22), (255, 255, 255, 230), 3)
    im.alpha_composite(t_, ((w - t_.width) // 2, (h - t_.height) // 2)); return im

def tile(fr, x, y, w, h, k, focus):
    if k <= 0: return
    im, d = ss_canvas(w, h)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], 26 * SS, fill=(24, 24, 28, 245),
                        outline=(GOLD + (220,)) if focus else (255, 255, 255, 40), width=2 * SS)
    put(fr, ss_done(im, w, h), x, y + (1 - ease_out(k)) * 20, ease_out(k))

def house_icon(sz, col=GOLD, wline=3):
    im, d = ss_canvas(sz, sz); u = sz * SS
    pts = [(0.18, 0.5), (0.5, 0.2), (0.82, 0.5), (0.82, 0.84), (0.18, 0.84), (0.18, 0.5)]
    d.line([(x * u, y * u) for x, y in pts], fill=col + (255,), width=wline * SS, joint="curve")
    d.rectangle([0.44 * u, 0.62 * u, 0.56 * u, 0.84 * u], outline=col + (255,), width=wline * SS)
    return ss_done(im, sz, sz)

# ---------------------------------------------------------------- scenes (screen space)
def sc_hook(t):                                       # 0 - 7.7 "la caja pequeña y estrecha ya es cosa del pasado"
    fr = V.GROUND.copy()
    V.label_swap(fr, [(0.35, "Casas modulares"), (3.84, "Cosa del pasado")], t)
    s = 54; dims = (6.0, 2.4, 2.6); o = (W / 2 - (dims[0] - dims[1]) / 2 * S.C30 * s, CYP + 10 - (dims[2] - (dims[0] + dims[1]) * 0.5) / 2 * s)
    fade = 1 - 0.65 * ease_io(prog(t, 4.95, 0.4))
    S.iso_plot(fr, o, s, 9, 5, -1.5, -1.3, ease_out(prog(t, 0.4, 0.6)), 0.7 * fade)
    S.iso_box(fr, o, s, dims, ease_out(prog(t, 0.6, 1.2)), 0, 0, fade, windows=False, grey=True)
    kl = prog(t, 2.05, 0.4)
    if kl > 0:                                        # the old idea, struck through on "pasado"
        f = MF(500, 26); tx = text("CAJA PEQUEÑA Y ESTRECHA", f, (200, 200, 206, 255), 4)
        x, y = W / 2 - tx.width / 2, 860
        put(fr, tx, x, y + (1 - ease_out(kl)) * 12, ease_out(kl) * (0.5 + 0.5 * fade))
        ks = ease_io(prog(t, 4.6, 0.35))
        if ks > 0:
            ln, dl = ss_canvas(W, 8); hair(dl, [(x - 10, 4), (x - 10 + (tx.width + 20) * ks, 4)], GOLD, 1, 3)
            fr.alpha_composite(ss_done(ln, W, 8), (0, int(y + tx.height / 2 - 2)))
    return fr

def sc_size(t):                                       # 7.7 - 12.9 "casas amplias de 100 e incluso 200 m²"
    fr = V.GROUND.copy(); dy_ = DY(t); eyebrow(fr, "Casas amplias", X0, EY, prog(t, 7.8, 0.45))
    k1 = ease_io(prog(t, 10.2, 0.8)); k2 = ease_io(prog(t, 11.4, 0.9))
    m2 = int(round(lerp(0, 100, k1) + 100 * k2))
    if k1 > 0:                                        # big thin number, on the alignment line
        n = text(str(m2), MF(200, 150), GOLD + (255,), -3); u = text("m²", MF(300, 48), (255, 255, 255, 255))
        put(fr, n, X0 - 6, EY + 34 + dy_, ease_out(k1)); put(fr, u, X0 + text("200", MF(200, 150), GOLD, -3).width + 6, EY + 34 + dy_ + n.height - u.height - 30, ease_out(k1))
    f = dy_ / 345; s = 28 + 16 * f; dx, dy = 12.0, 8.4; dz = 3.3 + 3.3 * k2
    c0 = S.iso(dx / 2, dy / 2, 1.65, (W / 2 + 120 - (dx - dy) / 2 * S.C30 * 28, 640), 28)     # where it sits over Alena
    c = S.iso(dx / 2, dy / 2, 1.65, (0, 0), s)                                                # full screen: centred, bigger
    o = (lerp(c0[0], W / 2, f) - c[0], lerp(c0[1], H / 2 - 40, f) - c[1])
    S.iso_plot(fr, o, s, 16, 12, -2, -1.8, ease_out(prog(t, 7.85, 0.7)), 0.8)
    kd = ease_out(prog(t, 8.0, 1.3))
    S.iso_box(fr, o, s, (dx, dy, dz), kd, ease_io(prog(t, 10.3, 0.6)), 0, ease_out(clamp(kd * 2)))
    P = lambda x, y, z: S.iso(x, y, z, o, s)
    if k2 > 0.9:                                      # storey line on the second floor
        lay, d = ss_canvas(W, H); hair(d, [P(0, dy, 3.3), P(dx, dy, 3.3), P(dx, 0, 3.3)], GOLD, 0.7, 1.5); fr.alpha_composite(ss_done(lay, W, H))
    kf = ease_io(prog(t, 11.9, 0.7))
    if kf > 0: villa(fr, P, dx, dy, dz, kf)
    return fr

def villa(fr, P, dx, dy, dz, k):
    """the line volume turns into our house: white shell, big glazing with warm light, terrace deck"""
    lay, d = ss_canvas(W, H)
    def poly(pts, col, a=255): d.polygon([(x * SS, y * SS) for x, y in (P(*q) for q in pts)], fill=col + (a,))
    def front(x0, x1, z0, z1, col, a=255): poly([(x0, dy, z0), (x1, dy, z0), (x1, dy, z1), (x0, dy, z1)], col, a)
    def side(y0, y1, z0, z1, col, a=255): poly([(dx, y0, z0), (dx, y1, z0), (dx, y1, z1), (dx, y0, z1)], col, a)
    poly([(-0.6, dy, 0), (dx + 0.6, dy, 0), (dx + 0.6, dy + 3.0, 0), (-0.6, dy + 3.0, 0)], (52, 44, 36))      # deck
    for j in range(1, 12):                                                                              # deck boards
        x = -0.6 + j * (dx + 1.2) / 12; hair(d, [P(x, dy, 0), P(x, dy + 3.0, 0)], (30, 26, 22), 0.8, 1)
    poly([(0, 0, dz), (dx, 0, dz), (dx, dy, dz), (0, dy, dz)], (236, 236, 238))                          # roof
    front(0, dx, 0, dz, (214, 214, 218)); side(0, dy, 0, dz, (168, 168, 176))                          # white aluminium shell
    for zb in (0.0, 3.3):                                                                               # glazing per storey
        x0, x1 = (0.9, dx - 0.9) if zb == 0 else (3.6, dx - 0.9)
        front(x0, x1, zb + 0.35, zb + 2.95, (24, 24, 28))
        front(x0 + 0.1, x1 - 0.1, zb + 0.35, zb + 1.5, (196, 150, 92), 120)                            # warm interior light
        for xx in np.linspace(x0, x1, 5)[1:-1]: hair(d, [P(xx, dy, zb + 0.35), P(xx, dy, zb + 2.95)], (12, 12, 14), 1, 2)
        side(2.4, dy - 2.4, zb + 0.6, zb + 2.95, (24, 24, 28)); side(2.5, dy - 2.5, zb + 0.6, zb + 1.6, (196, 150, 92), 90)
    hair(d, [P(0, dy, 3.3), P(dx, dy, 3.3), P(dx, 0, 3.3)], (150, 150, 158), 1, 1.5)                    # floor line
    for a, b in ((P(0, dy, dz), P(dx, dy, dz)), (P(dx, dy, dz), P(dx, 0, dz)), (P(dx, dy, 0), P(dx, dy, dz))):
        hair(d, [a, b], GOLD, 0.9, 2)                                                                   # gold edge accents
    fr.alpha_composite(with_alpha(ss_done(lay, W, H), k))

def sc_interior(t):                                   # 12.9 - 16.9 "lo que te va a sorprender está en el interior"
    fr = V.GROUND.copy()
    dy_ = DY(t); V.label_swap(fr, [(13.0, "Lo que sorprende"), (15.7, "Está en el interior")], t, EY + dy_)
    c = V.wipe_seq(V.card_img(A.INTERIORS[0], 1.02 + 0.06 * prog(t, 13.0, 4.0)), [(15.75, V.card_img(A.INTERIORS[2], 1.02 + 0.04 * prog(t, 15.75, 1.2)))], t)
    V.show_card(fr, c, V.CARD_CY + dy_, ease_out(prog(t, 13.0, 0.5)))
    return fr

NODES = [("Luces", -1, -1), ("Clima", 1, -1), ("Persianas", -1, 1), ("Acceso", 1, 1)]
def sc_hub(t):                                        # 16.9 - 22.5 "sistema domótico premium, sin ningún coste adicional"
    dy_ = DY(t); fr = V.GROUND.copy(); eyebrow(fr, "Domótica premium", X0, EY + dy_ * 1.2, prog(t, 17.0, 0.45))
    cx, cy = W / 2, CYP + 20 + dy_; dxn, dyn = 300, 170
    kh = ease_out(prog(t, 17.2, 0.5))
    lay, d = ss_canvas(W, H)
    for i, (lab, sx, sy) in enumerate(NODES):         # orthogonal hairline connectors, drawn in one by one
        k = ease_io(prog(t, 18.3 + i * 0.3, 0.5))
        if k <= 0: continue
        nx, ny = cx + sx * dxn, cy + sy * dyn
        path = [(cx + sx * 95, cy), (cx + sx * 190, cy), (cx + sx * 190, ny), (nx - sx * 125, ny)]
        hair(d, A.polyline_part(path, k), GOLD, 0.9, 2)
        if k >= 1:                                    # a small pulse travelling along the line
            u = ((t - 18.3 - i * 0.3) * 0.6) % 1; px, py = A.polyline_part(path, u)[-1]
            d.ellipse([(px - 5) * SS, (py - 5) * SS, (px + 5) * SS, (py + 5) * SS], fill=GOLD + (255,))
    fr.alpha_composite(ss_done(lay, W, H))
    for i, (lab, sx, sy) in enumerate(NODES):
        kn = prog(t, 18.6 + i * 0.3, 0.4)
        if kn > 0: put(fr, node(lab), cx + sx * dxn, cy + sy * dyn + (1 - ease_out(kn)) * 12, ease_out(kn), "mm")
    if kh > 0:                                        # the hub: our house, gold
        hb, d = ss_canvas(180, 180)
        d.rounded_rectangle([0, 0, 180 * SS - 1, 180 * SS - 1], 40 * SS, fill=(28, 26, 24, 255), outline=GOLD + (255,), width=3 * SS)
        hb = ss_done(hb, 180, 180); hb.alpha_composite(house_icon(110), (35, 30))
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g.alpha_composite(hb, (int(cx - 90), int(cy - 90)))
        glow(fr, with_alpha(g, kh), 26, 0.5)
    kp = prog(t, 20.7, 0.45)
    if kp > 0:                                        # "sin ningún coste adicional"
        pl = pill("INCLUIDO  ·  0 € EXTRA", MF(600, 26), (20, 20, 22, 255), GOLD + (255,), (26, 12))
        put(fr, pl, cx, cy + dyn + 120 + (1 - ease_out(kp)) * 12, ease_out(kp), "mm")
    return fr

def sc_lock(t):                                       # 22.5 - 26.6 "olvídate de las llaves · la puerta se abre con un solo toque"
    fr = V.GROUND.copy()
    dy_ = DY(t); V.label_swap(fr, [(22.6, "Olvídate de las llaves"), (24.36, "Un solo toque")], t, EY + dy_ * 1.2)
    cx, cy = W / 2, CYP + 30 + dy_
    kk = ease_out(prog(t, 22.65, 0.45)); kg = ease_io(prog(t, 23.75, 0.5))
    if kk > 0 and kg < 1:                             # Polina's keys fall away
        kw = 440; key = A.KEYS.resize((kw, round(A.KEYS.height * kw / A.KEYS.width)), Image.LANCZOS)
        put(fr, key, cx, cy - 20 + kg * 80, kk * (1 - kg), "mm")
    kp = ease_out(prog(t, 24.3, 0.5))
    if kp > 0:                                        # smart lock panel, line art
        pw, ph = 230, 430; im, d = ss_canvas(pw, ph)
        d.rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], 40 * SS, fill=(24, 24, 28, 250), outline=(255, 255, 255, 70), width=2 * SS)
        tc = ease_io(prog(t, 26.05, 0.25)); r = 46
        d.ellipse([(pw / 2 - r) * SS, (ph * 0.42 - r) * SS, (pw / 2 + r) * SS, (ph * 0.42 + r) * SS],
                  fill=GOLD + (int(40 + 215 * tc),), outline=GOLD + (255,), width=3 * SS)
        panel = ss_done(im, pw, ph)
        st = text("ABIERTO" if tc > 0.5 else "CERRADO", MF(600, 22), (GOLD + (255,)) if tc > 0.5 else (170, 170, 178, 255), 4)
        panel.alpha_composite(st, ((pw - st.width) // 2, int(ph * 0.75)))
        put(fr, panel, cx, cy + (1 - kp) * 30, kp, "mm")
        rp = prog(t, 26.1, 0.9)                       # touch ripple
        if 0 < rp < 1:
            rr, dr = ss_canvas(W, H); R = (46 + 140 * ease_out(rp)) * SS; c0 = (cx * SS, (cy - ph / 2 + ph * 0.42) * SS)
            dr.ellipse([c0[0] - R, c0[1] - R, c0[0] + R, c0[1] + R], outline=GOLD + (int(230 * (1 - rp)),), width=2 * SS)
            fr.alpha_composite(ss_done(rr, W, H))
    return fr

HOT = [(0.36, 0.12), (0.72, 0.30), (0.12, 0.55)]
def sc_hud(t):                                        # 26.6 - 32.6 "controlar toda tu casa como en una película de ciencia ficción"
    fr = V.GROUND.copy()
    V.label_swap(fr, [(26.75, "Control total"), (31.0, "Ciencia ficción")], t)
    kin = ease_out(prog(t, 26.75, 0.5))
    r = V.show_card(fr, V.card_img(A.INTERIORS[2], 1.03 + 0.05 * prog(t, 26.75, 5.5)), V.CARD_CY, kin)
    if not r: return fr
    x0, y0 = r; w, h = V.CWD, V.CHD
    lay, d = ss_canvas(W, H); kb = ease_out(prog(t, 27.4, 0.6)); L_ = 54 * kb
    for (bx, by, sx, sy) in ((x0 + 22, y0 + 22, 1, 1), (x0 + w - 22, y0 + 22, -1, 1), (x0 + 22, y0 + h - 22, 1, -1), (x0 + w - 22, y0 + h - 22, -1, -1)):
        if L_ > 0: hair(d, [(bx, by + sy * L_), (bx, by), (bx + sx * L_, by)], GOLD, 1, 3)   # HUD corner brackets
    ks = prog(t, 28.3, 3.8)
    if 0 < ks < 1:                                    # scan line sweeping the room
        yy = y0 + 30 + (h - 60) * ((ks * 2) % 1)
        hair(d, [(x0 + 30, yy), (x0 + w - 30, yy)], GOLD, 0.55, 2)
    for i, (hx, hy) in enumerate(HOT):                # hotspots
        k = prog(t, 28.9 + i * 0.35, 0.4)
        if k <= 0: continue
        px, py = x0 + w * hx, y0 + h * hy; pr = 14 + 5 * math.sin((t - 28.9) * 4 + i)
        d.ellipse([(px - pr) * SS, (py - pr) * SS, (px + pr) * SS, (py + pr) * SS], outline=GOLD + (int(255 * k),), width=2 * SS)
        d.ellipse([(px - 5) * SS, (py - 5) * SS, (px + 5) * SS, (py + 5) * SS], fill=GOLD + (int(255 * k),))
    fr.alpha_composite(ss_done(lay, W, H))
    return fr

TILES = [("Luces", 33.05), ("Temperatura", 33.85), ("Persianas", 34.9), ("Pantalla oculta", 36.65)]
def sc_tiles(t):                                      # 32.6 - 38.3 lights, temperature, blinds, hidden screen
    fr = V.GROUND.copy(); eyebrow(fr, "Todo bajo control", X0, EY, prog(t, 32.7, 0.45))
    tw_, th_, gap = (W - 2 * X0 - 24) // 2, 270, 24; ys = (EY + 62, EY + 62 + th_ + gap)
    cur = max([i for i, (_, t0) in enumerate(TILES) if t >= t0 - 0.05] + [-1])
    for i, (lab, t0) in enumerate(TILES):
        k = prog(t, t0 - 0.05, 0.45)
        if k <= 0: continue
        x = X0 + (i % 2) * (tw_ + gap); y = ys[i // 2]; a = ease_out(k)
        tile(fr, x, y, tw_, th_, k, i == cur)
        put(fr, text(lab.upper(), MF(600, 22), (255, 255, 255, 200), 4), x + 30, y + 30, a)
        lay, d = ss_canvas(W, H); kk = ease_io(prog(t, t0 + 0.1, 0.8))
        if i == 0:                                    # lights: value + slider
            put(fr, text(f"{int(80 * kk)}%", MF(200, 96), GOLD + (255,), -2), x + 26, y + 70, a)
            hair(d, [(x + 30, y + th_ - 46), (x + tw_ - 30, y + th_ - 46)], (255, 255, 255), 0.2, 2)
            hair(d, [(x + 30, y + th_ - 46), (x + 30 + (tw_ - 60) * 0.8 * kk, y + th_ - 46)], GOLD, 1, 4)
        elif i == 1:                                  # temperature: thin number + arc
            put(fr, text(f"{int(round(lerp(26, 22, kk)))}°", MF(200, 96), GOLD + (255,), -2), x + 26, y + 70, a)
            cxa, cya, R = x + tw_ - 95, y + th_ / 2 + 20, 60
            d.arc([(cxa - R) * SS, (cya - R) * SS, (cxa + R) * SS, (cya + R) * SS], 135, 405, fill=(255, 255, 255, 50), width=4 * SS)
            d.arc([(cxa - R) * SS, (cya - R) * SS, (cxa + R) * SS, (cya + R) * SS], 135, 135 + 270 * (0.4 + 0.2 * kk), fill=GOLD + (255,), width=5 * SS)
        elif i == 2:                                  # blinds: slats coming down
            put(fr, text(f"{int(60 * kk)}%", MF(200, 96), GOLD + (255,), -2), x + 26, y + 70, a)
            wx0, wy0, ww, wh = x + tw_ - 170, y + 70, 140, 160
            d.rectangle([wx0 * SS, wy0 * SS, (wx0 + ww) * SS, (wy0 + wh) * SS], outline=(255, 255, 255, 80), width=2 * SS)
            for j in range(int(8 * 0.6 * kk) + 1):
                yy = wy0 + 10 + j * 18; hair(d, [(wx0 + 8, yy), (wx0 + ww - 8, yy)], GOLD, 0.9, 3)
        else:                                         # hidden screen sliding down out of the ceiling
            sx0, sw = x + 40, tw_ - 80; slot = y + 76; sh_ = 130 * kk
            hair(d, [(sx0 - 10, slot), (sx0 + sw + 10, slot)], (255, 255, 255), 0.6, 3)
            if sh_ > 2:
                d.rectangle([sx0 * SS, slot * SS, (sx0 + sw) * SS, (slot + sh_) * SS], fill=(40, 38, 34, 255), outline=GOLD + (255,), width=2 * SS)
        fr.alpha_composite(with_alpha(ss_done(lay, W, H), a))
    return fr

def sc_voice(t):                                      # 38.3 - 40.6 "todo responde a tus órdenes de voz"
    fr = V.GROUND.copy(); eyebrow(fr, "Control por voz", X0, EY, prog(t, 38.4, 0.45))
    k = ease_out(prog(t, 38.45, 0.5)); cx, cy = W / 2, CYP + 20; n = 33; bw, gapb = 12, 12
    lay, d = ss_canvas(W, H); x0 = cx - (n * bw + (n - 1) * gapb) / 2
    for i in range(n):                                # bars driven by her real voice
        dt = (i - n // 2) * 0.03; amp = vo(t - abs(dt)) * (1 - abs(i - n // 2) / (n * 0.62))
        hgt = max(6, 260 * clamp(amp) * k); x = x0 + i * (bw + gapb)
        d.rounded_rectangle([x * SS, (cy - hgt / 2) * SS, (x + bw) * SS, (cy + hgt / 2) * SS], bw / 2 * SS,
                            fill=(GOLD if abs(i - n // 2) < 9 else (255, 255, 255)) + (int(255 * k * (1 if abs(i - n // 2) < 9 else 0.35)),))
    fr.alpha_composite(ss_done(lay, W, H))
    return fr

ROWS = ["Sistema domótico premium", "Cerradura inteligente", "Luces y climatización", "Persianas automáticas", "Pantalla retráctil"]
def sc_included(t):                                   # 40.6 - 47.5 "no es un lujo... es nuestro estándar, incluido en el precio"
    fr = V.GROUND.copy()
    V.label_swap(fr, [(40.7, "Lo mejor de todo"), (44.84, "Nuestro estándar")], t)
    y0, rh = EY + 60, 92; f = MF(300, 38); fi = MF(600, 22)
    lay, d = ss_canvas(W, H)
    for i in range(len(ROWS) + 1):
        k = ease_out(prog(t, 40.8 + i * 0.25, 0.6))
        hair(d, [(X0, y0 + i * rh), (X0 + (W - 2 * X0) * k, y0 + i * rh)], (255, 255, 255), 0.16, 1)
    fr.alpha_composite(ss_done(lay, W, H))
    for i, s_ in enumerate(ROWS):
        k = ease_out(prog(t, 40.9 + i * 0.25, 0.45))
        if k <= 0: continue
        cy = y0 + i * rh + rh / 2
        put(fr, text(s_, f, (255, 255, 255, 235)), X0, cy - 26 + (1 - k) * 10, k)
        ki = ease_out(prog(t, 45.0 + i * 0.12, 0.35))      # "incluido" marks appear on "nuestro estándar"
        if ki > 0: put(fr, text("INCLUIDO", fi, GOLD + (255,), 4), W - X0, cy - 14, ki, "rl")
    kt = ease_out(prog(t, 46.1, 0.5))
    if kt > 0:                                        # total row: what it adds to the price
        yt = y0 + len(ROWS) * rh + 34
        put(fr, text("COSTE ADICIONAL", MF(600, 22), (255, 255, 255, 200), 4), X0, yt + 34, kt)
        put(fr, text("0 €", MF(200, 92), GOLD + (255,), -2), W - X0, yt, kt, "rl")
    return fr

def sc_cta(t):                                        # 47.5 - end: the house of your dreams, button on the seam
    fr = V.GROUND.copy()
    V.label_swap(fr, [(47.6, "Mensaje privado"), (50.2, "La casa de tus sueños")], t)
    V.show_card(fr, V.card_img(A.HOUSE, 1.02 + 0.08 * prog(t, 47.5, 5.0), 0.6, 0.5), V.CARD_CY, ease_out(prog(t, 47.55, 0.5)))
    return fr

V.SCENES[:] = [(0.0, 7.7, sc_hook), (7.7, 12.9, sc_size), (12.9, 16.9, sc_interior), (16.9, 22.5, sc_hub),
               (22.5, 26.6, sc_lock), (26.6, 32.6, sc_hud), (32.6, 38.3, sc_tiles), (38.3, 40.6, sc_voice),
               (40.6, 47.5, sc_included), (47.5, 99, sc_cta)]

# ---------------------------------------------------------------- sound: a few soft ticks only, no music
def make_sfx(path):
    SR = L.SR; total = np.zeros((int(TOTAL * SR) + SR * 2, 2))
    def add(t, snd, g):
        i = max(0, int(t * SR)); seg = snd * L.db(g); total[i:i + len(seg)] += seg[:len(total) - i]
    for tt in (20.7, 26.1, 46.1): add(tt, L.sfx_tick(), -17)
    add(CTA_T + 0.45, L.sfx_tick(), -12)
    add(LOGO_T, L.sfx_boom(), -12); add(LOGO_T + 0.05, L.sfx_shimmer(), -24)
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(total, -1, 1) * 32767).astype("<i2").tobytes())

def extract():
    d = TMP + "/v2_frames"; os.makedirs(d, exist_ok=True)
    if not glob.glob(d + "/*.jpg"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.SRC, "-vf", f"fps={FPS},scale={W}:{H}", "-q:v", "2", d + "/g_%04d.jpg"], check=True)
    A.GIRL[:] = sorted(glob.glob(d + "/*.jpg"))
def _frame(i):
    if not A.GIRL: extract()
    p = f"{TMP}/v2o/{i:04d}.jpg"; V.compose(i / FPS).convert("RGB").save(p, quality=95, subsampling=0); return p
def run(out):
    extract(); os.makedirs(TMP + "/v2o", exist_ok=True); sfx = TMP + "/v2_sfx.wav"; make_sfx(sfx); n = int(round(TOTAL * FPS))
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/v2o/%04d.jpg", "-i", A.SRC, "-i", sfx,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[v];[2:a]aresample=44100[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        extract()
        for tt in sys.argv[3].split(","): V.compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
