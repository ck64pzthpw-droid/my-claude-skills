#!/usr/bin/env python3
# Style frames for the v2 look (stills for Polina's approval). Usage: wr_style_frames.py OUT_DIR
import os, sys, glob
from PIL import Image, ImageDraw
import numpy as np
import wr_style as S
from wr_style import MF, text, put, eyebrow, headline, GOLD, W, H, PANEL_CY
import wr15_luban as L

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.environ.get("TMP_DIR", "/tmp")
FR = sorted(glob.glob(TMP + "/a90_frames/*.png"))
PANEL_H, SRC_Y = 1040, 175
LOGO = Image.open(HERE + "/refs/wr_logo_white.png").convert("RGBA")
WM = LOGO.resize((300, round(LOGO.height * 300 / LOGO.width)), Image.LANCZOS)

def girl(t, y0):
    return Image.open(FR[int(round(t * 25))]).convert("RGBA"), y0
def grad():
    a = np.zeros((H, 1), np.float32); y = np.arange(H)
    a[:, 0] = np.clip((y - 1150) / 770, 0, 1) ** 1.2 * 0.62 + np.clip((330 - y) / 330, 0, 1) * 0.38
    g = np.zeros((H, W, 4), np.uint8); g[..., 3] = (np.repeat(a, W, 1) * 255).astype(np.uint8); return Image.fromarray(g)
GRAD = grad()
def subs(fr, small, big, cy=1530):
    fs, fb = MF(500, 44), MF(600, 92)
    a = text(small, fs, (255, 255, 255, 255)); b = text(big, fb, (255, 255, 255, 255), -1.5)
    wmax = max(a.width, b.width); x0 = (W - wmax) / 2; y = cy - (a.height + b.height - 20) / 2
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lay.alpha_composite(a, (int(x0), int(y))); lay.alpha_composite(b, (int(x0 - 4), int(y + a.height - 18)))
    from PIL import ImageFilter
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.55)))
    fr.alpha_composite(sh, (0, 4)); fr.alpha_composite(lay)
def split(panel, t, y0, small, big):
    fr = Image.new("RGBA", (W, H), S.INK + (255,))
    g, y0 = girl(t, y0); fr.alpha_composite(g, (0, PANEL_H - y0))
    fr.alpha_composite(panel.crop((0, SRC_Y, W, SRC_Y + PANEL_H)), (0, 0))
    fr.alpha_composite(Image.new("RGBA", (W, 2), GOLD + (200,)), (0, PANEL_H - 1))
    fr.alpha_composite(GRAD); fr.alpha_composite(WM, ((W - WM.width) // 2, 92)); subs(fr, small, big); return fr.convert("RGB")

X0 = 90                                                   # left alignment line for labels
TOP = SRC_Y + 240                                         # first text row under the watermark

# 1 ---- precision: the S70 as isometric line art on the plot, real dimensions
def f_precision():
    fr = S.GROUND.copy()
    eyebrow(fr, "Precisión milimétrica", X0, TOP, 1)
    headline(fr, "Fabricada", "en fábrica", X0, TOP + 52, 1, 58)
    s = 44; o = (W / 2 - 4 * S.C30 * s + 10, 870 - 2.05 * s)
    S.iso_plot(fr, o, s, 15, 7, -1.8, -1.8)
    S.s70_iso(fr, o, s, 1.0, 1.0)
    P = lambda x, y, z: S.iso(x, y, z, o, s)
    S.iso_dim(fr, P(0, 3.4, 0), P(11.4, 3.4, 0), (-30, 52), "11 400 mm", 1)
    S.iso_dim(fr, P(11.4, 3.4, 0), P(11.4, 0, 0), (46, 26), "3 400", 1, MF(500, 26))
    S.iso_dim(fr, P(11.4, 0, 0), P(11.4, 0, 3.3), (52, 0), "3 300", 1, MF(500, 26))
    return fr

# 2 ---- 90 days: thin big number, four-step timeline
def f_90():
    fr = S.GROUND.copy()
    eyebrow(fr, "Del contrato a las llaves", X0, TOP, 1)
    n = text("90", MF(200, 330), GOLD + (255,), -6); u = text("días", MF(300, 74), (255, 255, 255, 255))
    wtot = n.width + 18 + u.width; x = (W - wtot) / 2; y = PANEL_CY - 230
    put(fr, n, x, y); put(fr, u, x + n.width + 18, y + n.height - u.height - 52)
    steps = ["Contrato", "Fábrica", "Envío", "Llaves"]; y_l = PANEL_CY + 175; xa, xb = X0 + 80, W - X0 - 80
    lay, d = L.ss_canvas(W, H); S.hair(d, [(xa, y_l), (xb, y_l)], (255, 255, 255), 0.22, 1.5)
    S.hair(d, [(xa, y_l), (xb, y_l)], GOLD, 1.0, 3)
    fr.alpha_composite(L.ss_done(lay, W, H))
    f = MF(500, 28)
    for i, st in enumerate(steps):
        xx = xa + (xb - xa) * i / 3
        dot, dd = L.ss_canvas(30, 30); dd.ellipse([3 * L.SS, 3 * L.SS, 27 * L.SS, 27 * L.SS], fill=S.INK + (255,), outline=GOLD + (255,), width=3 * L.SS)
        if i == 3: dd.ellipse([9 * L.SS, 9 * L.SS, 21 * L.SS, 21 * L.SS], fill=GOLD + (255,))
        put(fr, L.ss_done(dot, 30, 30), xx, y_l, 1, "mm")
        put(fr, text(st.upper(), f, (255, 255, 255, 200), 3), xx, y_l + 30, 1, "ml")
    return fr

# 3 ---- fixed price: grey dashed "traditional" budget climbs, our gold line stays flat
def f_price():
    fr = S.GROUND.copy()
    eyebrow(fr, "Precio cerrado", X0, TOP, 1)
    headline(fr, "Lo que firmas", "es lo que pagas", X0, TOP + 52, 1, 58)
    gx0, gx1, gy_top, gy_bot = X0, W - X0, PANEL_CY - 90, PANEL_CY + 300
    lay, d = L.ss_canvas(W, H)
    for i in range(4): S.hair(d, [(gx0, lerp_(gy_bot, gy_top, i / 3)), (gx1, lerp_(gy_bot, gy_top, i / 3))], (255, 255, 255), 0.12, 1, dash=7)
    pts = [(0, .12), (.14, .2), (.27, .16), (.4, .34), (.52, .3), (.66, .55), (.78, .5), (.9, .78), (1, .95)]
    P = [(gx0 + (gx1 - gx0) * x, gy_bot - (gy_bot - gy_top) * y) for x, y in pts]
    area = P + [(gx1, gy_bot), (gx0, gy_bot)]
    d.polygon([(x * L.SS, y * L.SS) for x, y in area], fill=(255, 255, 255, 14))
    S.hair(d, P, (170, 170, 178), 0.8, 2, dash=9)
    fr.alpha_composite(L.ss_done(lay, W, H))
    yf = P[0][1]; g, d2 = L.ss_canvas(W, H); S.hair(d2, [(gx0, yf), (gx1, yf)], GOLD, 1, 4); S.glow(fr, L.ss_done(g, W, H), 10, 0.9)
    lab = MF(500, 24)
    put(fr, text("OBRA TRADICIONAL", lab, (190, 190, 198, 255), 3), gx1, P[-1][1] - 44, 1, "rl")
    put(fr, text("WHITEROOM", lab, GOLD + (255,), 3), gx0, yf - 52)
    # marker on our line + value
    mx = gx0 + (gx1 - gx0) * 0.66
    m, dm = L.ss_canvas(60, 60); c = 30 * L.SS
    dm.ellipse([c - 26 * L.SS, c - 26 * L.SS, c + 26 * L.SS, c + 26 * L.SS], fill=GOLD + (60,))
    dm.ellipse([c - 12 * L.SS, c - 12 * L.SS, c + 12 * L.SS, c + 12 * L.SS], fill=GOLD + (255,)); dm.ellipse([c - 5 * L.SS, c - 5 * L.SS, c + 5 * L.SS, c + 5 * L.SS], fill=(20, 20, 22, 255))
    put(fr, L.ss_done(m, 60, 60), mx, yf, 1, "mm")
    pl = S.pill("+0 €", MF(600, 40), (20, 20, 22, 255), GOLD + (255,), (26, 12))
    put(fr, pl, mx, yf + 70, 1, "mm")
    return fr
def lerp_(a, b, k): return a + (b - a) * k

# 4 ---- photo in a thin frame, label and facts on one alignment line
def f_photo():
    fr = S.GROUND.copy()
    eyebrow(fr, "Lista para vivir", X0, TOP, 1)
    import wr_alena90 as A
    w, h = W - 2 * X0, 560
    x, y = S.frame_card(fr, L.cover(A.PR + "interior-collage.png", w, h, 0.5, 0.5, crop=(81, 26, 822, 494)), W / 2, PANEL_CY + 40, w, h)
    f = MF(400, 28); facts = ["S70", "38,7 m²", "2 dormitorios", "Llave en mano"]
    xx = X0
    for i, s_ in enumerate(facts):
        t = text(s_.upper(), f, (255, 255, 255, 210) if i else GOLD + (255,), 3); put(fr, t, xx, y + h + 26); xx += t.width + 18
        if i < len(facts) - 1:
            dot = Image.new("RGBA", (6, 6), GOLD + (200,)); put(fr, dot, xx, y + h + 26 + t.height / 2 - 3); xx += 6 + 18
    return fr

# 5 ---- presenter full screen with the lower third (blue + white), Montserrat subtitles
def f_lower():
    fr = Image.new("RGBA", (W, H)); g, _ = girl(6.0, 0); fr.alpha_composite(g); fr.alpha_composite(GRAD)
    fr.alpha_composite(WM, ((W - WM.width) // 2, 92))
    BLUE = (30, 80, 210); x, y = X0, 1150
    tag = text("DIRECTORA · WHITEROOM GROUP", MF(600, 24), BLUE + (255,), 4)
    tb = Image.new("RGBA", (tag.width + 32, 46), (255, 255, 255, 255)); tb.alpha_composite(tag, (16, (46 - tag.height) // 2))
    nm = text("Alena", MF(500, 70), (255, 255, 255, 255), -1)
    nb = Image.new("RGBA", (nm.width + 52, 104), BLUE + (255,)); nb.alpha_composite(nm, (26, (104 - nm.height) // 2 - 2))
    fr.alpha_composite(tb, (x, y)); fr.alpha_composite(nb, (x, y + 52))
    subs(fr, "de", "WhiteRoom Group,"); return fr.convert("RGB")

if __name__ == "__main__":
    out = sys.argv[1]
    split(f_precision(), 13.6, 210, "con precisión", "milimétrica").save(out + "/1-precision.jpg", quality=90)
    split(f_90(), 24.9, 240, "En solo", "90 días,").save(out + "/2-90-dias.jpg", quality=90)
    split(f_price(), 36.0, 450, "Con nosotros, el precio es", "cerrado").save(out + "/3-precio.jpg", quality=90)
    split(f_photo(), 29.0, 300, "y lista para", "entrar a vivir").save(out + "/4-interior.jpg", quality=90)
    f_lower().save(out + "/5-plashka.jpg", quality=90)
