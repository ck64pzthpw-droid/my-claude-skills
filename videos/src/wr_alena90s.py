#!/usr/bin/env python3
# Alena «90 días», style v2 (Polina's references + whiteroomgroup site): dark ground with a faint grid, hairlines,
# Montserrat, one gold accent, isometric line art, framed photos, everything on one left alignment line.
# Presenter mechanics (jump-cut covers, split screen, word timings) come from wr_alena90.py.
# Usage: wr_alena90s.py preview OUT_PREFIX t1,t2,...   |   wr_alena90s.py full OUT.mp4
import os, sys, math, subprocess, glob, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import wr15_luban as L
import wr_alena90 as A
import wr_style as S
from wr_style import MF, text, put, eyebrow, headline, hair, glow, pill, INK
from wr15_luban import W, H, GOLD, SS, clamp, prog, ease_out, ease_io, lerp, with_alpha, ss_canvas, ss_done

HERE = A.HERE; TMP = A.TMP; FPS = A.FPS
VID_END, LOGO_T, TOTAL = A.VID_END, A.LOGO_T, A.TOTAL
PANEL_H = 960                      # split screen: panel above, Alena below (more room for her and the subtitles)
CYP = 575                          # centre of the content area in the panel (under the watermark)
X0 = 90                            # left alignment line (on the grid)
EY = 238                           # eyebrow row
SUB_CY = 1420                      # subtitles: higher and smaller than v3 (Polina)

# y0 ~ 95 px above the top of her head in split screen
A.EDGE[-2:] = [(48.45, 1), (48.8, 2), (99, 2)]   # Alena stays in split under the CTA, panel covers only for the last second
A.SHOTS[:] = [(0.0, 1.0, 0.5, 335), (3.96, 1.0, 0.5, 240), (14.16, 1.0, 0.5, 200), (19.56, 1.0, 0.5, 273),
              (25.64, 1.0, 0.5, 335), (33.56, 1.45, 0.5, 480), (40.16, 1.0, 0.5, 345)]

# ---------------------------------------------------------------- ground
def _ground():
    a = np.zeros((H, W, 3), np.float32) + np.array(INK, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    a += (np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - CYP) / 560) ** 2)) * 9)[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for x in range(0, W + 1, 90): d.line([(x, 0), (x, H)], fill=(255, 255, 255, 8), width=1)
    for y in range(CYP % 90, H, 90): d.line([(0, y), (W, y)], fill=(255, 255, 255, 8), width=1)
    im.alpha_composite(g); return im
GROUND = _ground()

def _grad():
    a = np.zeros((H, 1), np.float32); y = np.arange(H)
    a[:, 0] = np.clip((y - 1180) / 700, 0, 1) ** 1.2 * 0.6 + np.clip((300 - y) / 300, 0, 1) * 0.35
    g = np.zeros((H, W, 4), np.uint8); g[..., 3] = (np.repeat(a, W, 1) * 255).astype(np.uint8); return Image.fromarray(g)
GRAD = _grad()

LOGO = Image.open(HERE + "/refs/wr_logo_white.png").convert("RGBA")
def logo_w(w): return LOGO.resize((w, round(LOGO.height * w / LOGO.width)), Image.LANCZOS)
WM = with_alpha(logo_w(280), 0.92); WM_POS = ((W - WM.width) // 2, 84)
END_LOGO = logo_w(720)

# ---------------------------------------------------------------- subtitles in Montserrat, smaller
F_SUB_S = MF(500, 38); SUB_MAXW = 860
def build_chunks():
    chunks = []; wi = 0
    for txt in A.CH_TXT:
        c = L.Chunk(); rows = []
        for ln in txt.split("/"):
            ln = ln.strip(); big = ln.startswith("="); row = []
            for w in ln.lstrip("=").split(): row.append(A.WL[wi]); wi += 1
            rows.append((big, row))
        c.rows = rows; c.start = rows[0][1][0][1] - 0.05; chunks.append(c)
    for a, b in zip(chunks, chunks[1:]): a.end = b.start
    chunks[-1].end = 49.6
    for c in chunks:
        lay = []
        for big, row in c.rows:
            if big:
                s_ = " ".join(w for w, _ in row); size = 76
                while size > 44:
                    f = MF(600, size); tr = -0.02 * size
                    if L.tw(f, s_, tr) <= SUB_MAXW: break
                    size -= 2
                lay.append((big, row, f, tr, size * 1.04))
            else: lay.append((big, row, F_SUB_S, 0.0, 48))
        widths = [L.tw(f, " ".join(w for w, _ in row), tr) for big, row, f, tr, lh in lay]
        x0 = (W - max(widths)) / 2; th = sum(l[4] for l in lay); y = SUB_CY - th / 2; items = []
        for big, row, f, tr, lh in lay:
            x = x0; sp = f.getlength(" ") + tr; yoff = -lh * 0.14 if big else 0
            for w, ts in row:
                items.append((w, ts, big, f, tr, x, y + yoff)); x += L.tw(f, w, tr) + sp
            y += lh
        c.items = items
    return chunks
L.SUB_CY = SUB_CY; L.CHUNKS = build_chunks()

# ---------------------------------------------------------------- cards
CWD, CHD = 900, 568                                   # photo card (same 1.58 ratio as the source crops)
def card_img(img, z=1.0, cx=0.5, cy=0.5): return L.zoom(img, z, cx, cy).resize((CWD, CHD), Image.LANCZOS).convert("RGBA")
def wipe_seq(base, steps, t):
    """base card, then (t0, img) wipes with a thin gold scan line"""
    c = base
    for t0, img in steps:
        k = ease_io(prog(t, t0, 0.6))
        if k > 0: c = L.wipe(c, img, k * (CWD + 80), 80, line=k < 1)
    return c
def show_card(fr, c, cy, k):
    """framed photo card sliding up 24 px as it fades in"""
    if k <= 0: return None
    return S.frame_card(fr, c, W / 2, cy + (1 - k) * 24, CWD, CHD, k)
CARD_TOP = EY + 62                                    # cards start right under the eyebrow (tight, per Polina)
CARD_CY = CARD_TOP + CHD / 2

def label_swap(fr, items, t, y=EY):
    """eyebrow that changes text over time: items = [(t_in, text), ...]"""
    for i, (t0, s_) in enumerate(items):
        t1 = items[i + 1][0] if i + 1 < len(items) else 1e9
        k = prog(t, t0, 0.45) * (1 - ease_io(prog(t, t1 - 0.25, 0.25)))
        if k > 0: eyebrow(fr, s_, X0, y, k)

# ---------------------------------------------------------------- assets
SKETCH, HERO = L.SKETCH, L.HERO
FACTORY, STEEL, PLANCARD = A.FACTORY, A.STEEL, A.PLANCARD
INTERIORS, HOUSE, KEYS, CONTRACT = A.INTERIORS, A.HOUSE, A.KEYS, A.CONTRACT

# ---------------------------------------------------------------- scenes (screen space; the panel shows rows 0..edge)
def sc_hook(t):                                       # 0 - 4.6  Polina's sketch becomes the real S70
    fr = GROUND.copy(); kin = ease_out(prog(t, 0.25, 0.5))
    eyebrow(fr, "Casas modulares", X0, EY, prog(t, 0.4, 0.5))
    z = 1.0 + 0.03 * prog(t, 0, 2.2) + 0.08 * ease_io(prog(t, 2.2, 2.0))
    paper = Image.new("RGBA", (CWD, CHD), L.PAPER + (255,))
    c = L.wipe(paper, card_img(SKETCH, z, 0.5, 0.55), ease_io(prog(t, 0.3, 0.8)) * (CWD + 140), 140, line=False)
    kp = ease_io(prog(t, 1.3, 0.7))
    if kp > 0: c = L.wipe(c, card_img(HERO, z, 0.5, 0.55), kp * (CWD + 80), 80, line=kp < 1)
    show_card(fr, c, CARD_CY, kin)
    return fr

def sc_factory(t):                                    # 9.7 - 14.7 factory -> steel frame -> plan with millimetres
    fr = GROUND.copy(); kin = ease_out(prog(t, 9.9, 0.5))
    label_swap(fr, [(10.0, "Fabricadas en fábrica"), (13.2, "Precisión milimétrica")], t)
    c = wipe_seq(card_img(FACTORY, 1.03 + 0.06 * prog(t, 9.9, 3.0)),
                 [(12.45, card_img(STEEL, 1.02 + 0.05 * prog(t, 12.45, 2.0), 0.45, 0.6)),
                  (13.25, card_img(PLANCARD, 1.0 + 0.04 * prog(t, 13.25, 1.5)))], t)
    show_card(fr, c, CARD_CY, kin)
    return fr

def sc_plot(t):                                       # 14.7 - 19.3 the module arrives on your plot, finished
    fr = GROUND.copy()
    label_swap(fr, [(14.85, "Llega a tu parcela"), (17.0, "Completamente terminada")], t)
    s = 46; o = (W / 2 - 4 * S.C30 * s, CYP + 40 - 2.05 * s)
    S.iso_plot(fr, o, s, 15, 7, -1.8, -1.8, ease_out(prog(t, 14.8, 0.6)), ease_out(prog(t, 14.8, 0.3)))
    kd = prog(t, 14.95, 0.7); land = ease_io(prog(t, 15.2, 0.65))
    kg = ease_io(prog(t, 15.85, 0.5))
    if kd > 0: S.s70_iso(fr, o, s, kd, kg, lift=4.0 * (1 - land), alpha=ease_out(clamp(kd * 2)))
    P = lambda x, y, z: S.iso(x, y, z, o, s)
    S.iso_dim(fr, P(0, 3.4, 0), P(11.4, 3.4, 0), (-30, 52), "11 400 mm", prog(t, 16.4, 0.7))
    S.iso_dim(fr, P(11.4, 3.4, 0), P(11.4, 0, 0), (46, 26), "3 400", prog(t, 16.8, 0.6), MF(500, 26))
    S.iso_dim(fr, P(11.4, 0, 0), P(11.4, 0, 3.3), (52, 0), "3 300", prog(t, 17.1, 0.6), MF(500, 26))
    kl = prog(t, 18.05, 0.4)
    if kl > 0:                                        # "listas para instalar"
        pl = pill("LISTA PARA INSTALAR", MF(600, 26), (20, 20, 22, 255), GOLD + (255,), (24, 12))
        put(fr, pl, X0, 880 + (1 - ease_out(kl)) * 14, ease_out(kl))
    return fr

SIN = [("Obras interminables", 19.35, 20.35), ("Escombros", 21.15, 21.75), ("Retrasos constantes", 22.35, 23.0)]
def sc_sin(t):                                        # 19.3 - 24.1 three things you will not have
    fr = GROUND.copy(); eyebrow(fr, "Sin sorpresas", X0, EY, prog(t, 19.3, 0.45))
    f = MF(300, 58); fi = MF(500, 24); y0 = EY + 90; rh = 150
    lay, d = ss_canvas(W, H)
    for i in range(len(SIN) + 1):
        k = ease_out(prog(t, 19.3 + i * 0.12, 0.6))
        hair(d, [(X0, y0 + i * rh), (X0 + (W - 2 * X0) * k, y0 + i * rh)], (255, 255, 255), 0.16, 1)
    fr.alpha_composite(ss_done(lay, W, H))
    for i, (s_, t0, ts) in enumerate(SIN):
        k = ease_out(prog(t, t0, 0.45))
        if k <= 0: continue
        cy = y0 + i * rh + rh / 2; ks = ease_io(prog(t, ts, 0.45)); g = int(lerp(255, 110, ks))
        put(fr, text(f"0{i + 1}", fi, GOLD + (255,), 2), X0, cy - 30 + (1 - k) * 14, k)
        tx = text(s_, f, (g, g, g, 255), -0.5); tx_x = X0 + 80
        put(fr, tx, tx_x, cy - tx.height / 2 - 4 + (1 - k) * 14, k)
        if ks > 0:
            ln, dl = ss_canvas(W, 8); hair(dl, [(tx_x, 4), (tx_x + (tx.width - 6) * ks, 4)], GOLD, 1, 3)
            fr.alpha_composite(ss_done(ln, W, 8), (0, int(cy - 2)))
    return fr

STEPS = ["Contrato", "Fábrica", "Envío", "Llaves"]
FACTS = ["S70", "38,7 m²", "2 dormitorios", "Llave en mano"]   # facts row under the interiors
def sc_90(t):                                         # 24.1 - 30.95 90 days -> keys -> finished interior
    fr = GROUND.copy()
    label_swap(fr, [(24.15, "Del contrato a las llaves"), (26.25, "Tus llaves"), (27.7, "Lista para vivir")], t)
    kout = ease_io(prog(t, 26.1, 0.35))
    if kout < 1:
        a = 1 - kout; kr = ease_io(prog(t, 24.4, 1.3)); n = int(round(90 * kr))
        num = text(str(n), MF(200, 300), GOLD + (255,), -6); ref = text("90", MF(200, 300), GOLD + (255,), -6)
        u = text("días", MF(300, 66), (255, 255, 255, 255))
        wtot = ref.width + 16 + u.width; x = (W - wtot) / 2; y = EY + 40
        kin = ease_out(prog(t, 24.2, 0.35))
        put(fr, num, x + ref.width - num.width, y + (1 - kin) * 20, a * kin)
        put(fr, u, x + ref.width + 16, y + ref.height - u.height - 46, a * ease_out(prog(t, 25.3, 0.35)))
        y_l = y + ref.height + 40; xa, xb = X0 + 80, W - X0 - 80
        lay, d = ss_canvas(W, H)
        hair(d, [(xa, y_l), (xb, y_l)], (255, 255, 255), 0.2 * a, 1.5)
        if kr > 0: hair(d, [(xa, y_l), (lerp(xa, xb, kr), y_l)], GOLD, a, 3)
        fr.alpha_composite(ss_done(lay, W, H))
        for i, st in enumerate(STEPS):
            xx = xa + (xb - xa) * i / 3; on = kr >= i / 3 - 1e-6
            dot, dd = ss_canvas(30, 30)
            dd.ellipse([3 * SS, 3 * SS, 27 * SS, 27 * SS], fill=INK + (255,), outline=(GOLD if on else (90, 90, 96)) + (255,), width=3 * SS)
            if i == 3 and kr >= 1: dd.ellipse([9 * SS, 9 * SS, 21 * SS, 21 * SS], fill=GOLD + (255,))
            put(fr, ss_done(dot, 30, 30), xx, y_l, a * kin, "mm")
            put(fr, text(st.upper(), MF(500, 26), (255, 255, 255, 220 if on else 120), 3), xx, y_l + 30, a * kin, "ml")
    kk = ease_out(prog(t, 26.25, 0.5)); kg = ease_io(prog(t, 27.6, 0.35))
    if kk > 0 and kg < 1:                             # Polina's keys
        kw = 560; key = KEYS.resize((kw, round(KEYS.height * kw / KEYS.width)), Image.LANCZOS)
        key = key.rotate(lerp(-14, 0, kk) + 1.5 * math.sin(max(0, t - 26.25) * 3), resample=Image.BICUBIC, expand=True)
        a = kk * (1 - kg); sh, pad = L.shadow_of(key, 24, 0.5 * a)
        cx, cy = W / 2, CYP + 20
        fr.alpha_composite(sh, (int(cx - key.width / 2 - pad), int(cy - key.height / 2 - pad + 24)))
        put(fr, key, cx, cy + (1 - kk) * 30, a, "mm")
    kc = ease_out(prog(t, 27.7, 0.5))
    if kc > 0:                                        # three real interiors, then the facts on the alignment line
        c = wipe_seq(card_img(INTERIORS[0], 1.02 + 0.05 * prog(t, 27.7, 3.2)),
                     [(28.85, card_img(INTERIORS[1], 1.02 + 0.04 * prog(t, 28.85, 1.5))),
                      (29.95, card_img(INTERIORS[2], 1.02 + 0.04 * prog(t, 29.95, 1.2)))], t)
        r = show_card(fr, c, CARD_CY, kc)
        kf = ease_out(prog(t, 28.0, 0.5))
        if r and kf > 0:
            xx = X0 + (W - 2 * X0 - CWD) / 2; yy = CARD_TOP + CHD + 26
            for i, s_ in enumerate(FACTS):
                tt = text(s_.upper(), MF(400, 26), (GOLD + (255,)) if i == 0 else (255, 255, 255, 210), 3)
                put(fr, tt, xx, yy, kf); xx += tt.width + 18
                if i < len(FACTS) - 1: put(fr, Image.new("RGBA", (6, 6), GOLD + (200,)), xx, yy + tt.height / 2 - 3, kf); xx += 24
    return fr

CHART = [(0, .1), (.14, .18), (.27, .14), (.4, .33), (.52, .29), (.66, .54), (.78, .49), (.9, .76), (1, .92)]
def sc_price(t):                                      # 30.95 - 37.3 budgets that keep rising vs our fixed price
    fr = GROUND.copy()
    label_swap(fr, [(31.0, "Presupuesto"), (34.85, "Precio cerrado")], t)
    gx0, gx1 = X0, W - X0; gy_top, gy_bot = EY + 120, EY + 600
    kin = ease_out(prog(t, 31.0, 0.5))
    lay, d = ss_canvas(W, H)
    for i in range(4):
        yy = lerp(gy_bot, gy_top, i / 3); hair(d, [(gx0, yy), (lerp(gx0, gx1, kin), yy)], (255, 255, 255), 0.12, 1, dash=7)
    P = [(gx0 + (gx1 - gx0) * x, gy_bot - (gy_bot - gy_top) * y) for x, y in CHART]
    kr = ease_io(prog(t, 31.35, 2.7)); fade = 1 - 0.45 * ease_io(prog(t, 35.0, 0.6))
    if kr > 0:
        part = A.polyline_part(P, kr)
        d.polygon([(x * SS, y * SS) for x, y in part + [(part[-1][0], gy_bot), (gx0, gy_bot)]], fill=(255, 255, 255, int(16 * fade)))
        hair(d, part, (175, 175, 182), 0.85 * fade, 2, dash=9)
    fr.alpha_composite(ss_done(lay, W, H))
    lab = MF(500, 24)
    if kr > 0.75:                                     # label sits above the end of the grey line, clear of it
        put(fr, text("OBRA TRADICIONAL", lab, (190, 190, 198, 255), 3), gx1, P[-1][1] - 52, ease_out(prog(kr, 0.75, 0.25)) * fade, "rl")
    yf = P[0][1]; kf = ease_io(prog(t, 34.95, 0.9))
    if kf > 0:
        g, d2 = ss_canvas(W, H); hair(d2, [(gx0, yf), (lerp(gx0, gx1, kf), yf)], GOLD, 1, 4); glow(fr, ss_done(g, W, H), 10, 0.9)
        put(fr, text("WHITEROOM", lab, GOLD + (255,), 3), gx0, yf + 22, ease_out(prog(t, 35.2, 0.4)))   # under the line
    km = prog(t, 36.45, 0.4)
    if km > 0:
        mx = gx0 + (gx1 - gx0) * 0.62
        m, dm = ss_canvas(64, 64); c = 32 * SS; r1 = 28 * (0.6 + 0.4 * ease_out(km))
        dm.ellipse([c - r1 * SS, c - r1 * SS, c + r1 * SS, c + r1 * SS], fill=GOLD + (55,))
        dm.ellipse([c - 12 * SS, c - 12 * SS, c + 12 * SS, c + 12 * SS], fill=GOLD + (255,))
        dm.ellipse([c - 5 * SS, c - 5 * SS, c + 5 * SS, c + 5 * SS], fill=(20, 20, 22, 255))
        put(fr, ss_done(m, 64, 64), mx, yf, ease_out(km), "mm")
        pl = pill("PRECIO CERRADO", MF(600, 26), (20, 20, 22, 255), GOLD + (255,), (24, 12))
        put(fr, pl, mx, yf - 66 + (1 - ease_out(km)) * 12, ease_out(km), "mm")
    return fr

def sc_contract(t):                                   # 37.3 - 41.0 what you sign is what you pay
    fr = GROUND.copy(); eyebrow(fr, "Contrato", X0, EY, prog(t, 37.3, 0.45))
    headline(fr, "Lo que firmas", "es lo que pagas", X0, EY + 44, prog(t, 37.35, 0.7), 50)
    kin = ease_out(prog(t, 37.45, 0.5))
    pw = 900; doc = CONTRACT.resize((pw, round(CONTRACT.height * pw / CONTRACT.width)), Image.LANCZOS)
    cx, cy = W - doc.width / 2 + 110 + (1 - kin) * 40, EY + 150 + doc.height / 2    # bigger, runs off the right edge
    sh, pad = L.shadow_of(doc, 26, 0.5 * kin)
    fr.alpha_composite(sh, (int(cx - doc.width / 2 - pad), int(cy - doc.height / 2 - pad + 18))); put(fr, doc, cx, cy, kin, "mm")
    kb = prog(t, 40.05, 0.4)
    if kb > 0:                                        # "ni un céntimo más"
        pl = pill("+0 €", MF(600, 44), (20, 20, 22, 255), GOLD + (255,), (30, 14))
        sc = 0.8 + 0.2 * ease_out(kb)
        pl = pl.resize((round(pl.width * sc), round(pl.height * sc)), Image.LANCZOS)
        put(fr, pl, W - X0, EY + 50, ease_out(kb), "rl")
    return fr

def sc_3m(t):                                         # 41.0 - 45.2 your own house in three months
    fr = GROUND.copy()
    label_swap(fr, [(42.2, "Tu propia casa"), (44.4, "En tan solo"), (45.5, "Mensaje privado")], t)
    kin = ease_out(prog(t, 42.2, 0.5))
    r = show_card(fr, card_img(HOUSE, 1.02 + 0.08 * prog(t, 42.2, 3.0), 0.6, 0.5), CARD_CY, kin)
    k3 = prog(t, 44.45, 0.45)
    if r and k3 > 0:                                  # big thin "3 meses" on the card's bottom-left, on the alignment line
        n = text("3", MF(300, 150), (255, 255, 255, 255), -2); u = text("meses", MF(400, 50), GOLD + (255,), 1)
        x, y = r[0] + 40, r[1] + CHD - 40 - n.height
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.alpha_composite(n, (int(x), int(y))); lay.alpha_composite(u, (int(x + n.width + 10), int(y + n.height - u.height - 26)))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.6)))
        fr.alpha_composite(with_alpha(sh, ease_out(k3))); fr.alpha_composite(with_alpha(lay, ease_out(k3)), (0, int((1 - ease_out(k3)) * 16)))
    return fr

CTA_T = 45.45
def sc_cta(t): return GROUND.copy()
CTA_CY = H / 2                         # Video 2 overrides it
def cta_button(fr, t):                                # white button at the true screen centre = on the panel seam
    cy = CTA_CY
    k = ease_out(prog(t, CTA_T, 0.45)); press = math.sin(math.pi * prog(t, CTA_T + 0.45, 0.22)) if CTA_T + 0.45 <= t <= CTA_T + 0.67 else 0
    f = MF(600, 58); tx = text("Escríbenos", f, (20, 20, 22, 255))
    bw, bh = tx.width + 150, 150; b, d = ss_canvas(bw, bh)
    d.rounded_rectangle([0, 0, bw * SS - 1, bh * SS - 1], bh * SS / 2, fill=(255, 255, 255, 255)); b = ss_done(b, bw, bh)
    b.alpha_composite(tx, ((bw - tx.width) // 2, (bh - tx.height) // 2 - 4))
    sc = (0.9 + 0.1 * k) * (1 - 0.05 * press); b = b.resize((round(bw * sc), round(bh * sc)), Image.LANCZOS)
    sh, pad = L.shadow_of(b, 26, 0.45 * k)
    fr.alpha_composite(sh, (int(W / 2 - b.width / 2 - pad), int(cy - b.height / 2 - pad + 16))); put(fr, b, W / 2, cy, k, "mm")
    rp = prog(t, CTA_T + 0.45, 0.7)                    # tap ripple, gold hairline
    if 0 < rp < 1:
        rr, dr = ss_canvas(W, 600); R = (bh / 2 + 70 * ease_out(rp)) * SS; c = (W / 2 * SS, 300 * SS); hw = (bw / 2 + 70 * ease_out(rp)) * SS
        dr.rounded_rectangle([c[0] - hw, c[1] - R, c[0] + hw, c[1] + R], R, outline=GOLD + (int(220 * (1 - rp)),), width=2 * SS)
        fr.alpha_composite(ss_done(rr, W, 600), (0, int(cy - 300)))
    return fr

SCENES = [(0.0, 4.6, sc_hook), (9.7, 14.7, sc_factory), (14.7, 19.3, sc_plot), (19.3, 24.1, sc_sin),
          (24.1, 30.95, sc_90), (30.95, 37.3, sc_price), (37.3, 41.0, sc_contract), (41.0, 48.6, sc_3m), (48.6, 99, sc_cta)]
XF = 0.3
def panel(t):
    fr = None
    for i, (a, b, fn) in enumerate(SCENES):
        if a - (XF if i else 0) <= t < b:
            img = fn(t); fr = img if fr is None else Image.blend(fr, img, ease_io(prog(t, a - XF, XF)))
    return fr if fr is not None else GROUND.copy()

# ---------------------------------------------------------------- lower third: dark, in our colours
F_LT_NAME = MF(500, 62); F_LT_TAG = MF(600, 22)
LT = (4.7, 9.25)                                       # lower third in / out
def lower_third(ov, t, x=X0, y=1150):
    kin = ease_io(prog(t, LT[0], 0.45)); kout = ease_io(prog(t, LT[1], 0.35)); k = kin * (1 - kout)
    if k <= 0: return
    name = text("Alena", F_LT_NAME, (255, 255, 255, 255)); tag = text("DIRECTORA · WHITEROOM GROUP", F_LT_TAG, GOLD + (255,), 4)
    nw, nh = name.width + 64, 96; tw_, th = tag.width + 40, 44
    box = Image.new("RGBA", (max(nw, tw_), nh + th), (0, 0, 0, 0)); d = ImageDraw.Draw(box)
    d.rectangle([0, 0, tw_ - 1, th - 1], fill=INK + (238,)); d.rectangle([0, th, nw - 1, th + nh - 1], fill=INK + (238,))
    d.line([(0, th), (0, th + nh - 1)], fill=GOLD + (255,), width=4)                       # gold accent on the name
    d.line([(4, th), (nw - 1, th)], fill=(255, 255, 255, 30), width=1)
    box.alpha_composite(tag, (20, (th - tag.height) // 2)); box.alpha_composite(name, (32, th + (nh - name.height) // 2 - 3))
    w = int(box.width * k)
    if w > 0: ov.alpha_composite(box.crop((0, 0, w, box.height)), (x, y))

# ---------------------------------------------------------------- compose
def compose(t):
    if t >= VID_END: fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        e = A.edge(t); e = e * PANEL_H / A.PANEL_H if e <= A.PANEL_H else lerp(PANEL_H, H, (e - A.PANEL_H) / (H - A.PANEL_H))
        split = clamp(e / PANEL_H); fr = Image.new("RGBA", (W, H), INK + (255,))
        if e < H:
            g, y0 = A.girl_frame(t, split); dy = int((PANEL_H - y0) * split + max(0, e - PANEL_H))
            fr.alpha_composite(g, (0, dy))
        ye = int(round(e))
        if ye > 0:
            pf = panel(t)
            p = pf.crop((0, PANEL_H - ye, W, PANEL_H)) if ye <= PANEL_H else pf.crop((0, 0, W, ye))
            fr.alpha_composite(p, (0, 0))
            if ye < H: fr.alpha_composite(Image.new("RGBA", (W, 2), GOLD + (190,)), (0, max(0, ye - 1)))
        fr.alpha_composite(GRAD)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ov.alpha_composite(WM, WM_POS)
        if LT[0] - 0.2 <= t <= LT[1] + 0.65: lower_third(ov, t)
        if t >= CTA_T: cta_button(ov, t)
        L.draw_subs(ov, t); fr.alpha_composite(ov)
    FB0 = LOGO_T - 0.45
    if t >= FB0:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), INK + (255,)), ease_io(prog(t, FB0, 0.45)))
        lk = ease_out(prog(t, LOGO_T, 1.0)) * (1 - ease_io(prog(t, TOTAL - 0.7, 0.6)))
        if lk > 0:
            sc = 0.97 + 0.03 * ease_out(prog(t, LOGO_T, 1.4))
            lg = END_LOGO.resize((round(END_LOGO.width * sc), round(END_LOGO.height * sc)), Image.LANCZOS)
            fr.alpha_composite(with_alpha(lg, lk), ((W - lg.width) // 2, (H - lg.height) // 2))
    return fr.convert("RGB")

# ---------------------------------------------------------------- sound: soft pops only, no music (Polina)
def make_sfx(path):
    SR = L.SR; total = np.zeros((int(TOTAL * SR) + SR * 2, 2))
    def add(t, snd, g):
        i = max(0, int(t * SR)); seg = snd * L.db(g); total[i:i + len(seg)] += seg[:len(total) - i]
    pop = L.sfx_pop
    # (the soft pop on every label change was removed: Polina found the repeated sound annoying)
    for tt in (15.85, 18.05, 36.45): add(tt, L.sfx_tick(), -17)
    for _, _, ts in SIN: add(ts, pop(900, 400, 0.14), -18)
    add(25.6, pop(1400, 900, 0.1), -17); add(40.05, pop(1300, 800, 0.12), -16); add(44.45, pop(1200, 700, 0.12), -17)
    add(CTA_T + 0.45, L.sfx_tick(), -12); add(CTA_T + 0.47, pop(1300, 700, 0.12), -15)
    add(LOGO_T, L.sfx_boom(), -12); add(LOGO_T + 0.05, L.sfx_shimmer(), -24)
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(total, -1, 1) * 32767).astype("<i2").tobytes())

def _frame(i):
    if not A.GIRL: A.extract()
    p = f"{TMP}/a90s_{i:04d}.png"; compose(i / FPS).save(p, compress_level=1); return p
def run(out):
    A.extract(); sfx = TMP + "/a90s_sfx.wav"; make_sfx(sfx); n = int(round(TOTAL * FPS))
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/a90s_%04d.png", "-i", A.SRC, "-i", sfx,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[v];[2:a]aresample=44100[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        A.extract()
        for tt in sys.argv[3].split(","): compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
