#!/usr/bin/env python3
# Visual system v2 for WhiteRoom videos (Polina's references, 2026-10-26):
# dark ground with a faint grid, 1 px hairlines, Montserrat as on the site, ONE gold accent per scene,
# thin isometric line art (rhymes with the cube logo), big thin numbers, small tracked labels with a gold dash.
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import wr15_luban as L
from wr15_luban import W, H, GOLD, SS, clamp, prog, ease_out, ease_io, lerp, with_alpha, ss_canvas, ss_done

HERE = os.path.dirname(os.path.abspath(__file__))
def MF(weight, size): return ImageFont.truetype(f"{HERE}/fonts/montserrat-latin-{weight}-normal.woff", size)

INK = (16, 16, 19)                                   # ground
LINE = (255, 255, 255)
GREY = (150, 150, 158)
PANEL_CY = 785                                       # centre of the visible panel (rows 175..1215 of the frame)

# ---------------------------------------------------------------- ground
def _ground():
    a = np.zeros((H, W, 3), np.float32) + np.array(INK, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    a += (np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - PANEL_CY) / 600) ** 2)) * 9)[..., None]   # soft light behind the focus
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g); step = 90
    for x in range(W // 2 % step, W, step): d.line([(x, 0), (x, H)], fill=(255, 255, 255, 9), width=1)
    for y in range(PANEL_CY % step, H, step): d.line([(0, y), (W, y)], fill=(255, 255, 255, 9), width=1)
    im.alpha_composite(g); return im
GROUND = _ground()

# ---------------------------------------------------------------- type
def text(s, f, fill=(255, 255, 255, 255), tr=0.0):
    w = L.tw(f, s, tr); asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(w) + 6, asc + desc + 6), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 3
    for c in s: d.text((x, 3), c, font=f, fill=fill); x += f.getlength(c) + tr
    return im
def put(fr, im, x, y, a=1.0, anchor="lt"):
    if a <= 0: return
    if anchor[0] == "m": x -= im.width / 2
    elif anchor[0] == "r": x -= im.width
    if anchor[1] == "m": y -= im.height / 2
    fr.alpha_composite(with_alpha(im, a), (int(round(x)), int(round(y))))

def eyebrow(fr, s, x, y, k, center=False):
    """small tracked gold label with a short gold dash in front: '——  PLAZO DE ENTREGA'"""
    if k <= 0: return
    f = MF(500, 26); t = text(s.upper(), f, GOLD + (255,), 0.42 * 26)
    dash = 56; gap = 22; wtot = dash + gap + t.width; x0 = x - wtot / 2 if center else x
    im, d = ss_canvas(dash + 2, 4); d.line([(0, 2 * SS), (dash * SS * ease_out(k), 2 * SS)], fill=GOLD + (255,), width=2 * SS)
    put(fr, ss_done(im, dash + 2, 4), x0, y + t.height / 2 - 2)
    put(fr, t, x0 + dash + gap + (1 - ease_out(k)) * 16, y, ease_out(k))

def headline(fr, l1, l2, x, y, k, size=64, center=False):
    """two-line title as on the site: white light caps, then gold light caps"""
    f = MF(300, size); a = text(l1.upper(), f, (255, 255, 255, 255), 0.02 * size)
    b = text(l2.upper(), f, GOLD + (255,), 0.02 * size) if l2 else None
    for i, im in enumerate([a] + ([b] if b else [])):
        kk = ease_out(clamp(k * 1.6 - i * 0.35))
        put(fr, im, (x - im.width / 2) if center else x, y + i * size * 1.08 + (1 - kk) * 20, kk)

def hair(d, pts, col, a, w=1.0, dash=None):
    """1 px (or w) line on an SS canvas; optional dash length in px"""
    c = col + (int(255 * a),); P = [(x * SS, y * SS) for x, y in pts]
    if not dash: d.line(P, fill=c, width=max(1, int(w * SS))); return
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(P, P[1:]):
        l = math.dist((x0, y0), (x1, y1)); n = max(1, int(l / (dash * SS)))
        for i in range(n):
            if (int(acc / (dash * SS)) + i) % 2: continue
            u0, u1 = i / n, (i + 1) / n
            d.line([(lerp(x0, x1, u0), lerp(y0, y1, u0)), (lerp(x0, x1, u1), lerp(y0, y1, u1))], fill=c, width=max(1, int(w * SS)))
        acc += l

def glow(fr, layer, r=18, a=0.9):
    g = layer.filter(ImageFilter.GaussianBlur(r)); fr.alpha_composite(with_alpha(g, a)); fr.alpha_composite(layer)

def pill(s, f, fg, bg, pad=(22, 10), outline=None):
    t = text(s, f, fg); w, h = t.width + 2 * pad[0], t.height + 2 * pad[1] - 6
    im, d = ss_canvas(w, h); d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], h * SS / 2, fill=bg, outline=outline, width=2 * SS if outline else 0)
    im = ss_done(im, w, h); im.alpha_composite(t, (pad[0], pad[1] - 4)); return im

# ---------------------------------------------------------------- isometry
C30, S30 = math.cos(math.radians(30)), 0.5
def iso(x, y, z, o, s): return (o[0] + (x - y) * C30 * s, o[1] + (x + y) * S30 * s - z * s)

def box_edges(x0, y0, z0, dx, dy, dz):
    v = [(x0 + a * dx, y0 + b * dy, z0 + c * dz) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    E = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    return v, E

def s70_iso(fr, o, s, k_draw=1.0, k_gold=0.0, lift=0.0, alpha=1.0):
    """S70 module 11.4 x 3.4 x 3.3 m as thin line art; k_draw draws the edges in, k_gold fills it with a gold glow"""
    dx, dy, dz = 11.4, 3.4, 3.3; z0 = lift
    P = lambda x, y, z: iso(x, y, z + z0, o, s)
    if k_gold > 0:
        lay, d = ss_canvas(W, H)
        top = [P(0, 0, dz), P(dx, 0, dz), P(dx, dy, dz), P(0, dy, dz)]
        front = [P(0, dy, 0), P(dx, dy, 0), P(dx, dy, dz), P(0, dy, dz)]
        side = [P(dx, 0, 0), P(dx, dy, 0), P(dx, dy, dz), P(dx, 0, dz)]
        for poly, a in ((top, 0.20), (front, 0.11), (side, 0.07)):
            d.polygon([(x * SS, y * SS) for x, y in poly], fill=GOLD + (int(255 * a * k_gold * alpha),))
        glow(fr, ss_done(lay, W, H), 40, 0.6)
    lay, d = ss_canvas(W, H)
    v, E = box_edges(0, 0, 0, dx, dy, dz)
    hidden = {(0, 1), (0, 2), (0, 4)}                         # edges from the far bottom corner
    for i, (a, b) in enumerate(E):
        kk = clamp(k_draw * len(E) - i * 0.6)
        if kk <= 0: continue
        pa, pb = P(*v[a]), P(*v[b]); pb = (lerp(pa[0], pb[0], kk), lerp(pa[1], pb[1], kk))
        col = GOLD if k_gold > 0.5 else LINE
        if (a, b) in hidden: hair(d, [pa, pb], LINE, 0.25 * alpha, 1.2, dash=8)
        else: hair(d, [pa, pb], col, 0.95 * alpha, 2.4)
    # window band on the long front face + door
    if k_draw >= 1:
        w0, w1 = 1.2, dx - 1.2
        hair(d, [P(w0, dy, 0.9), P(w1, dy, 0.9), P(w1, dy, 2.7), P(w0, dy, 2.7), P(w0, dy, 0.9)], LINE, 0.45 * alpha, 1.2)
        for xx in np.linspace(w0, w1, 6)[1:-1]: hair(d, [P(xx, dy, 0.9), P(xx, dy, 2.7)], LINE, 0.3 * alpha, 1.0)
    fr.alpha_composite(ss_done(lay, W, H))

def iso_plot(fr, o, s, nx=15, ny=7, x0=-1.8, y0=-1.8, k=1.0, a=1.0):
    """dashed isometric plot grid (1 m cells)"""
    lay, d = ss_canvas(W, H); kk = ease_out(k)
    for i in range(nx + 1):
        hair(d, [iso(x0 + i, y0, 0, o, s), iso(x0 + i, y0 + ny * kk, 0, o, s)], LINE, 0.22 * a, 1.2, dash=6)
    for j in range(ny + 1):
        hair(d, [iso(x0, y0 + j, 0, o, s), iso(x0 + nx * kk, y0 + j, 0, o, s)], LINE, 0.22 * a, 1.2, dash=6)
    fr.alpha_composite(ss_done(lay, W, H))

def iso_dim(fr, p0, p1, off, label, k, f=None):
    """dimension line parallel to p0-p1 shifted by off (screen px), ticks at both ends, label in a pill"""
    if k <= 0: return
    f = f or MF(500, 30)
    a = (p0[0] + off[0], p0[1] + off[1]); b = (p1[0] + off[0], p1[1] + off[1]); kk = ease_io(k)
    bb = (lerp(a[0], b[0], kk), lerp(a[1], b[1], kk))
    lay, d = ss_canvas(W, H)
    hair(d, [a, bb], GOLD, 1.0, 2.0)
    for p, q in ((p0, a), (p1, b)):
        if q is b and kk < 1: continue
        hair(d, [p, (q[0] + off[0] * 0.25, q[1] + off[1] * 0.25)], GOLD, 0.6, 1.0)
    fr.alpha_composite(ss_done(lay, W, H))
    kl = prog(k, 0.6, 0.4)
    if kl > 0:
        pl = pill(label, f, (20, 20, 22, 255), GOLD + (255,))
        put(fr, pl, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, ease_out(kl), "mm")

# ---------------------------------------------------------------- photo card: thin frame, no heavy shadow
def frame_card(fr, img, cx, cy, w, h, a=1.0, radius=22, z=1.0):
    c = L.zoom(img, z).resize((w, h), Image.LANCZOS).convert("RGBA") if img.size != (w, h) or z != 1 else img.convert("RGBA")
    c = L.rounded(c, radius)
    sh, pad = L.shadow_of(c, 30, 0.35 * a)
    x, y = int(cx - w / 2), int(cy - h / 2)
    fr.alpha_composite(sh, (x - pad, y - pad + 14)); fr.alpha_composite(with_alpha(c, a), (x, y))
    lay, d = ss_canvas(w + 2, h + 2)
    d.rounded_rectangle([0, 0, (w + 1) * SS, (h + 1) * SS], radius * SS, outline=(255, 255, 255, int(70 * a)), width=SS)
    fr.alpha_composite(ss_done(lay, w + 2, h + 2), (x - 1, y - 1))
    return x, y
