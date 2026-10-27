#!/usr/bin/env python3
# Video 1 «90 días» v6: Sergey's edits on top of wr_alena90s.py (style v2).
#  - hook: a real construction site (crane + bulldozer) that moves, then turns black and white on "construcción"
#  - "precisión milimétrica": E70 Pro plan 11 500 mm, then its 3D layout; the iso volume is the E70 Pro 11.5 x 4.3 x 2.5 m
#  - ending: the E70 at sunset full screen, our new logo slides in over it with the same sound
#  - layout alternates: Alena on top / design below 19.6-25.6 s; Alena full screen 0-1.5 s, 4.7-9.9 s and 40.9-42.8 s
#    (every switch happens under the full-screen panel, so no jump cut is ever visible)
# Usage: wr_video1v6.py preview OUT_PREFIX t1,t2,...   |   wr_video1v6.py full OUT.mp4
import os, sys, io, math, glob, subprocess
from multiprocessing import Pool
import numpy as np
import cairosvg
from PIL import Image, ImageDraw, ImageFilter
import wr15_luban as L
import wr_alena90 as A
import wr_alena90s as V
import wr_style as S
from wr_style import MF, text, put, pill, eyebrow, hair, INK
from wr15_luban import W, H, GOLD, SS, clamp, prog, ease_out, ease_io, lerp, with_alpha

HERE, TMP, FPS = V.HERE, V.TMP, V.FPS
PR = HERE + "/refs/polina/"
PANEL_H, X0, EY, CYP = V.PANEL_H, V.X0, V.EY, V.CYP
CWD, CHD = V.CWD, V.CHD

# ---------------------------------------------------------------- layout: when the panel is up, full, or Alena is alone
A.EDGE[:] = [(0.0, 0), (1.45, 0), (1.85, 1), (3.55, 1), (3.8, 2), (4.25, 2), (4.7, 0),
             (9.9, 0), (10.35, 1), (13.75, 1), (13.98, 2), (14.4, 2), (14.75, 1),
             (19.15, 1), (19.38, 2), (19.8, 2), (20.15, 1), (25.25, 1), (25.48, 2), (25.98, 2), (26.33, 1),
             (33.15, 1), (33.38, 2), (33.8, 2), (34.15, 1), (39.75, 1), (39.98, 2), (40.45, 2), (40.9, 0),
             (42.75, 0), (43.15, 1), (48.45, 1), (48.8, 2), (99, 2)]
FLIP = [(19.56, 25.64)]              # Alena on top, design below; toggled only while the panel covers all
def flipped(t): return any(a <= t < b for a, b in FLIP)
def screen_edge(t):
    e = A.edge(t)
    return e * PANEL_H / A.PANEL_H if e <= A.PANEL_H else lerp(PANEL_H, H, (e - A.PANEL_H) / (H - A.PANEL_H))
def flip_k(t):                                        # 0 = normal, 1 = Alena fully on top (drives subtitles, logo, gradient)
    return clamp((H - screen_edge(t)) / (H - PANEL_H)) if flipped(t) else 0.0

# ---------------------------------------------------------------- new logo (Polina, 2026-10-27), with a margin so the tips aren't cut
def _logo(w):
    png = cairosvg.svg2png(url=HERE + "/refs/wr_logo_final.svg", output_width=w * 2)
    im = Image.open(io.BytesIO(png)).convert("RGBA"); m = im.width // 60
    pad = Image.new("RGBA", (im.width + 2 * m, im.height + 2 * m), (0, 0, 0, 0)); pad.alpha_composite(im, (m, m))
    return pad.resize((w, round(pad.height * w / pad.width)), Image.LANCZOS)
V.WM = with_alpha(_logo(280), 0.92); V.WM_POS = ((W - V.WM.width) // 2, 84)
V.END_LOGO = _logo(600)                            # not too big (Polina)

# ---------------------------------------------------------------- assets
SITE = L.cover(PR + "kran-buldozer-clean.png", CWD * 2, CHD * 2, 0.55, 0.62)   # CAT lettering painted out
def _plan_card():
    c = Image.new("RGB", (CWD * 2, CHD * 2), L.PAPER); p = Image.open(PR + "e70-plan-11500.png").convert("RGB")
    w = CWD * 2 - 110; p = p.resize((w, round(p.height * w / p.width)), Image.LANCZOS)
    c.paste(p, ((CWD * 2 - p.width) // 2, (CHD * 2 - p.height) // 2)); return c
PLAN_E70 = _plan_card()
FACTORY_NEW = L.cover(PR + "fabrika-kapsula.png", CWD * 2, CHD * 2, 0.5, 0.5)   # Polina 2026-10-27: capsule on the factory floor
FACTORY_HALL = L.cover(PR + "fabrika-ceh.png", CWD * 2, CHD * 2, 0.5, 0.5)       # the hall with capsules in production
FACTORY_DET = L.cover(PR + "fabrika-detal.png", CWD * 2, CHD * 2, 0.55, 0.5)     # a worker fitting the shell: precision
PLAN_3D = L.cover(PR + "e70-plan-3d.png", CWD * 2, CHD * 2, 0.5, 0.5)
_end = Image.open(PR + "koncovka-e70-zakat.png").convert("RGB")
END_BIG = _end.resize((round(_end.width * H / _end.height), H), Image.LANCZOS)    # 2880 x 1920, panned across
V.INTERIORS[:] = [L.cover(PR + f, CWD * 2, CHD * 2, 0.5, 0.5) for f in      # Polina 2026-10-27: new interiors
                  ("interior-gostinaya.png", "interior-kuhnya.png", "interior-spalnya.png")]
V.FACTS[:] = ["E70 PRO", "50 m²", "2 dormitorios", "Llave en mano"]

# ---------------------------------------------------------------- scenes
DUST = [(0.10, 960, 850, 1.0), (0.45, 1090, 870, 1.3), (0.8, 1010, 820, 0.9), (1.15, 1150, 835, 1.1), (1.5, 900, 865, 1.2)]
def site_frame(t):
    """the construction photo, alive: slow push to the bulldozer, a little engine shake, dust from the blade"""
    z = 1.04 + 0.08 * ease_io(prog(t, 1.4, 2.6))
    cx = 0.58 + 0.0016 * math.sin(t * 23); cy = 0.64 + 0.0016 * math.sin(t * 31 + 1)
    im = L.zoom(SITE, z, cx, cy).convert("RGBA")
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sx, sy = im.width / SITE.width * z, im.height / SITE.height * z
    ox, oy = cx * SITE.width - SITE.width / (2 * z), cy * SITE.height - SITE.height / (2 * z)
    for ph, x, y, s in DUST:                          # puffs rise, grow and fade on a loop
        u = ((t + ph) / 1.75) % 1; r = (30 + 90 * u) * s; a = int(120 * (1 - u) * min(1, u * 5))
        px, py = (x + 40 * u - ox) * sx, (y - 70 * u - oy) * sy
        d.ellipse([px - r * sx, py - r * 0.7 * sy, px + r * sx, py + r * 0.7 * sy], fill=(196, 160, 118, a))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(18)))
    kg = ease_io(prog(t, 2.75, 0.7))                  # "construcción": the old way goes black and white
    if kg > 0:
        g = im.convert("L").convert("RGBA"); g = Image.blend(g, Image.new("RGBA", g.size, (24, 24, 26, 255)), 0.18)
        im = Image.blend(im, g, kg)
    return im.resize((CWD, CHD), Image.LANCZOS)

def sc_hook(t):                                       # 0 - 4.6 "olvídate de todo lo que creías saber sobre la construcción"
    fr = V.GROUND.copy()
    V.label_swap(fr, [(1.55, "La construcción"), (2.9, "Cosa del pasado")], t)
    V.show_card(fr, site_frame(t), V.CARD_CY, ease_out(prog(t, 1.45, 0.45)))
    return fr

def sc_factory(t):                                    # 9.7 - 15.6 three factory photos only (Polina), a little longer each
    fr = V.GROUND.copy(); kin = ease_out(prog(t, 9.9, 0.5))
    V.label_swap(fr, [(10.0, "Fabricadas en fábrica"), (13.2, "Precisión milimétrica")], t)
    c = V.wipe_seq(V.card_img(FACTORY_HALL, 1.03 + 0.05 * prog(t, 9.9, 2.0)),
                   [(11.75, V.card_img(FACTORY_NEW, 1.02 + 0.05 * prog(t, 11.75, 1.9))),
                    (13.45, V.card_img(FACTORY_DET, 1.02 + 0.07 * prog(t, 13.45, 2.2), 0.6, 0.5))], t)
    V.show_card(fr, c, V.CARD_CY, kin)
    return fr

E70 = (11.5, 4.3, 2.5)
def sc_plot(t):                                       # 14.7 - 19.3 the E70 Pro arrives on your plot, finished
    fr = V.GROUND.copy()
    V.label_swap(fr, [(15.65, "Llega a tu parcela"), (17.0, "Completamente terminada")], t)
    t = t - 0.8 if t < 18.0 else t                    # the module lands from 15.6 s, after the factory photos
    dx, dy, dz = E70; s = 44; o = (W / 2 - (dx - dy) / 2 * S.C30 * s, CYP + 20 - ((dx + dy) * 0.25 - dz / 2) * s)
    S.iso_plot(fr, o, s, 16, 8, -1.8, -1.8, ease_out(prog(t, 14.8, 0.6)), ease_out(prog(t, 14.8, 0.3)))
    kd = prog(t, 14.95, 0.7); land = ease_io(prog(t, 15.2, 0.65)); kg = ease_io(prog(t, 15.85, 0.5))
    if kd > 0: S.iso_box(fr, o, s, E70, kd, kg, 4.0 * (1 - land), ease_out(clamp(kd * 2)))
    P = lambda x, y, z: S.iso(x, y, z, o, s)
    S.iso_dim(fr, P(0, dy, 0), P(dx, dy, 0), (-30, 52), "11 500 mm", prog(t, 16.4, 0.7))
    S.iso_dim(fr, P(dx, dy, 0), P(dx, 0, 0), (46, 26), "4 300", prog(t, 16.8, 0.6), MF(500, 26))
    S.iso_dim(fr, P(dx, 0, 0), P(dx, 0, dz), (52, 0), "2 500", prog(t, 17.1, 0.6), MF(500, 26))
    kl = prog(t, 18.05, 0.4)
    if kl > 0:                                        # "listas para instalar"
        pl = pill("LISTA PARA INSTALAR", MF(600, 26), (20, 20, 22, 255), GOLD + (255,), (24, 12))
        put(fr, pl, X0, 880 + (1 - ease_out(kl)) * 14, ease_out(kl))
    return fr

def sc_3m(t):                                         # the house appears only after Alena's "en tan solo tres meses?"
    fr = V.GROUND.copy()
    V.label_swap(fr, [(42.85, "Tu propia casa"), (45.6, "Mensaje privado")], t)
    kin = ease_out(prog(t, 42.85, 0.45))
    r = V.show_card(fr, V.card_img(V.HOUSE, 1.02 + 0.07 * prog(t, 42.85, 5.0), 0.6, 0.5), V.CARD_CY, kin)
    k3 = prog(t, 44.45, 0.45)                         # "3 meses" on "tres meses?"
    if r and k3 > 0:                                  # big thin "3 meses" on the card's bottom-left
        n = text("3", MF(300, 150), (255, 255, 255, 255), -2); u = text("meses", MF(400, 50), GOLD + (255,), 1)
        x, y = r[0] + 40, r[1] + CHD - 40 - n.height
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lay.alpha_composite(n, (int(x), int(y))); lay.alpha_composite(u, (int(x + n.width + 10), int(y + n.height - u.height - 26)))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.6)))
        fr.alpha_composite(with_alpha(sh, ease_out(k3))); fr.alpha_composite(with_alpha(lay, ease_out(k3)), (0, int((1 - ease_out(k3)) * 16)))
    return fr

def end_photo(t):                                     # E70 at sunset, full screen: slow pan from the rock to the house
    x = lerp(340, 1520, ease_io(prog(t, 48.4, 4.4)))
    return END_BIG.crop((int(x), 0, int(x) + W, H)).convert("RGBA")
def sc_cta(t): return end_photo(t)

V.SCENES[:] = [(0.0, 4.6, sc_hook), (9.7, 15.6, sc_factory), (15.6, 19.3, sc_plot), (19.3, 24.1, V.sc_sin),
               (24.1, 30.95, V.sc_90), (30.95, 37.3, V.sc_price), (37.3, 41.0, V.sc_contract), (41.0, 48.6, sc_3m),
               (48.6, 99, sc_cta)]

# ---------------------------------------------------------------- subtitles follow the layout (over Alena's chest either way)
_draw_subs = L.draw_subs
def draw_subs(layer, t):
    k = flip_k(t)
    if k <= 0: return _draw_subs(layer, t)
    tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); _draw_subs(tmp, t)
    if k < 1: tmp = with_alpha(tmp, ease_io(abs(2 * k - 1)))   # while the panel moves: fade out, jump, fade in
    if k > 0.5: layer.alpha_composite(tmp, (0, 0), (0, PANEL_H - 300))
    else: layer.alpha_composite(tmp)
L.draw_subs = draw_subs

def _grad_f():                                        # gentle shade behind the subtitles when Alena is on top
    a = np.zeros((H, 1), np.float32); y = np.arange(H)
    a[:, 0] = np.where(y < PANEL_H, np.clip((y - 220) / 620, 0, 1) ** 1.2 * 0.5, 0)
    g = np.zeros((H, W, 4), np.uint8); g[..., :3] = INK; g[..., 3] = (np.repeat(a, W, 1) * 255).astype(np.uint8)
    return Image.fromarray(g, "RGBA")
GRAD_F = _grad_f()

def compose(t):
    VID_END, LOGO_T, TOTAL = V.VID_END, V.LOGO_T, V.TOTAL
    if t >= VID_END: fr = end_photo(t)
    else:
        e = screen_edge(t); fl = flipped(t); fk = flip_k(t)
        split = clamp(e / PANEL_H); fr = Image.new("RGBA", (W, H), INK + (255,))
        if e < H:
            g, y0 = A.girl_frame(t, split)
            dy = int((110 - y0) * split - max(0, e - PANEL_H)) if fl else int((PANEL_H - y0) * split + max(0, e - PANEL_H))
            fr.alpha_composite(g, (0, dy))
        ye = int(round(e))
        if ye > 0:
            pf = V.panel(t)
            if fl:                                    # panel lives at the bottom
                fr.alpha_composite(pf.crop((0, 0, W, ye)), (0, H - ye))
                if ye < H: fr.alpha_composite(Image.new("RGBA", (W, 2), GOLD + (190,)), (0, H - ye))
            else:
                p = pf.crop((0, PANEL_H - ye, W, PANEL_H)) if ye <= PANEL_H else pf.crop((0, 0, W, ye))
                fr.alpha_composite(p, (0, 0))
                if ye < H: fr.alpha_composite(Image.new("RGBA", (W, 2), GOLD + (190,)), (0, max(0, ye - 1)))
        if fk < 1: fr.alpha_composite(with_alpha(V.GRAD, 1 - fk))
        if fk > 0: fr.alpha_composite(with_alpha(GRAD_F, fk))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wy = V.WM_POS[1]                               # the small logo always stays at the top (Polina)
        ov.alpha_composite(V.WM, (V.WM_POS[0], int(wy)))
        if V.LT[0] - 0.2 <= t <= V.LT[1] + 0.65: V.lower_third(ov, t)
        if t >= V.CTA_T: V.cta_button(ov, t)
        L.draw_subs(ov, t); fr.alpha_composite(ov)
    FB0 = LOGO_T - 0.45
    if t >= FB0:                                      # the photo darkens and the logo slides in (Sergey: keep this everywhere)
        dark = Image.blend(end_photo(t), Image.new("RGBA", (W, H), INK + (255,)), 0.58)
        fr = Image.blend(fr, dark, ease_io(prog(t, FB0, 0.45)))
        lk = ease_out(prog(t, LOGO_T, 1.0))
        if lk > 0:
            sc = 0.97 + 0.03 * ease_out(prog(t, LOGO_T, 1.4))
            lg = V.END_LOGO.resize((round(V.END_LOGO.width * sc), round(V.END_LOGO.height * sc)), Image.LANCZOS)
            fr.alpha_composite(with_alpha(lg, lk), ((W - lg.width) // 2, (H - lg.height) // 2))
        fo = ease_io(prog(t, TOTAL - 0.7, 0.6))
        if fo > 0: fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), fo)
    return fr.convert("RGB")

# ---------------------------------------------------------------- render
def extract():
    d = TMP + "/a90j_frames"; os.makedirs(d, exist_ok=True)
    if not glob.glob(d + "/*.jpg"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.SRC, "-vf", f"fps={FPS},scale={W}:{H}", "-q:v", "2", d + "/g_%04d.jpg"], check=True)
    A.GIRL[:] = sorted(glob.glob(d + "/*.jpg"))
def _frame(i):
    if not A.GIRL: extract()
    p = f"{TMP}/v1o/{i:04d}.jpg"; compose(i / FPS).save(p, quality=95, subsampling=0); return p
def run(out):
    extract(); os.makedirs(TMP + "/v1o", exist_ok=True); sfx = TMP + "/v1_sfx.wav"; V.make_sfx(sfx); n = int(round(V.TOTAL * FPS))
    with Pool(os.cpu_count()) as pool: pool.map(_frame, range(n), chunksize=4)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", f"{TMP}/v1o/%04d.jpg", "-i", A.SRC, "-i", sfx,
        "-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[v];[2:a]aresample=44100[s];"
        "[v][s]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.84:level=false,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
        "-map", "0:v", "-map", "[a]", "-t", str(V.TOTAL), "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    if sys.argv[1] == "full": run(sys.argv[2])
    else:
        extract()
        for tt in sys.argv[3].split(","): compose(float(tt)).save(f"{sys.argv[2]}_{float(tt):05.2f}.jpg", quality=88)
