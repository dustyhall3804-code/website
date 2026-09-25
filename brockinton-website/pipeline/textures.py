"""Generate tileable PBR ground textures (albedo, normal, roughness).

These stand in for Poly Haven scans until the asset hosts are reachable
(see scripts/fetch-polyhaven.mjs). Output: build/tex/<name>_{albedo,normal,rough}.png
Every map tiles seamlessly because all noise is built in the frequency domain
on a torus.
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build", "tex")
os.makedirs(OUT, exist_ok=True)
N = 1024
rng = np.random.default_rng(7)

fy = np.fft.fftfreq(N)[:, None]
fx = np.fft.fftfreq(N)[None, :]
FR = np.sqrt(fx * fx + fy * fy)
FR[0, 0] = 1.0


def fbm(beta=2.0, lo=1.0, hi=N / 2, aniso=(1.0, 1.0), seed=None):
    """Tileable fractal noise, normalised to 0..1."""
    r = np.random.default_rng(seed) if seed is not None else rng
    w = r.standard_normal((N, N))
    F = np.fft.fft2(w)
    fr = np.sqrt((fx * aniso[0]) ** 2 + (fy * aniso[1]) ** 2)
    fr[0, 0] = 1.0
    k = fr * N
    amp = fr ** (-beta / 2) * (k >= lo) * np.exp(-(k / hi) ** 2)
    out = np.real(np.fft.ifft2(F * amp))
    out -= out.min()
    return out / out.max()


def worley(n_pts, seed=0):
    """Tileable F1/F2 cellular distance (pebbles, clods)."""
    r = np.random.default_rng(seed)
    pts = r.random((n_pts, 2)) * N
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    f1 = np.full((N, N), 1e9, np.float32)
    f2 = np.full((N, N), 1e9, np.float32)
    idx = np.zeros((N, N), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px)
        dx = np.minimum(dx, N - dx)
        dy = np.abs(yy - py)
        dy = np.minimum(dy, N - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        idx = np.where(closer, i, idx)
        f1 = np.where(closer, d, f1)
    return f1, f2, idx


def srgb_to_lin(c):
    c = np.asarray(c) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def ramp(t, stops):
    """Colour ramp: stops = [(pos, '#hex'), ...] -> sRGB float image."""
    pos = np.array([s[0] for s in stops])
    cols = np.array([[int(s[1][i:i + 2], 16) for i in (1, 3, 5)] for s in stops], np.float32)
    out = np.zeros(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


def normal_from_height(h, strength):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-gx, gy, np.ones_like(h)], -1)          # OpenGL convention (+Y up)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


def save(name, albedo, height, rough, strength):
    a = np.clip(albedo, 0, 255).astype(np.uint8)
    Image.fromarray(a).save(os.path.join(OUT, f"{name}_albedo.png"))
    n = normal_from_height(height, strength)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(OUT, f"{name}_normal.png"))
    Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, f"{name}_rough.png"))
    Image.fromarray((np.clip(height, 0, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, f"{name}_height.png"))
    print("wrote", name)


def shade(albedo, height, k=0.35):
    """Bake a hint of cavity darkening into albedo so small detail reads at distance."""
    cav = height - fbm(1.0, 1, 40, seed=99) * 0.0
    cav = (cav - cav.mean()) / (cav.std() + 1e-6)
    return albedo * (1 + k * np.clip(cav, -2, 2)[..., None] * 0.25)


# --- red Arkansas clay: dense, slightly blocky, bucket-tooth striations ------
def clay():
    base = fbm(2.2, 2, 300, seed=1)
    fine = fbm(1.4, 20, 512, seed=2)
    f1, f2, _ = worley(260, seed=3)
    clods = np.clip((f2 - f1) / 14.0, 0, 1)
    stri = fbm(2.0, 3, 400, aniso=(0.12, 1.0), seed=4)       # drag marks along one axis
    h = 0.5 * base + 0.22 * fine + 0.1 * clods + 0.25 * stri
    h = (h - h.min()) / (h.max() - h.min())
    t = 0.55 * base + 0.3 * fine + 0.15 * stri
    col = ramp(t, [(0.0, "#4a2217"), (0.35, "#733826"), (0.6, "#88472d"), (0.85, "#9c5a3b"), (1.0, "#b07a58")])
    ochre = fbm(2.5, 1, 60, seed=5)
    col = col * (1 - 0.35 * (ochre > 0.62)[..., None] * (ochre - 0.62)[..., None] * 4) + \
        ramp(ochre, [(0, "#9c5a2a"), (1, "#c28a45")]) * (0.35 * np.clip((ochre - 0.62) * 4, 0, 1))[..., None]
    rough = 0.78 + 0.18 * fine - 0.12 * (1 - clods)
    save("clay", shade(col, h), h, rough, 6.0)


# --- dark topsoil with roots -------------------------------------------------
def topsoil():
    base = fbm(2.0, 2, 380, seed=11)
    fine = fbm(1.2, 30, 512, seed=12)
    f1, f2, _ = worley(700, seed=13)
    crumbs = np.clip(1 - f1 / 9.0, 0, 1) ** 2
    roots = fbm(2.2, 4, 300, aniso=(1.0, 0.18), seed=14)
    roots = np.clip(1 - np.abs(roots - 0.5) * 30, 0, 1)
    h = 0.4 * base + 0.25 * fine + 0.35 * crumbs
    col = ramp(0.6 * base + 0.4 * fine, [(0, "#1e140d"), (0.4, "#33241a"), (0.75, "#4a3526"), (1, "#5d4634")])
    col = col * (1 - 0.6 * roots[..., None]) + np.array([150, 120, 80]) * 0.6 * roots[..., None]
    rough = 0.9 - 0.05 * crumbs
    save("topsoil", shade(col, h), h, rough, 5.0)


# --- sand and gravel -----------------------------------------------------------
def gravel():
    sand = fbm(1.0, 40, 512, seed=21)
    f1, f2, idx = worley(1400, seed=22)
    pebble = np.clip(1 - (f1 / (f2 + 1e-6)) * 1.6, 0, 1)
    tone = np.random.default_rng(23).random(1400)[idx]
    h = 0.35 * sand + 0.75 * np.sqrt(pebble)
    sand_col = ramp(sand, [(0, "#8c6d4c"), (0.5, "#b08d64"), (1, "#c9a87e")])
    peb_col = ramp(tone, [(0, "#6e6258"), (0.4, "#8f8173"), (0.7, "#a58c6c"), (1, "#c4b39c")])
    m = (pebble > 0.05)[..., None]
    col = np.where(m, peb_col * (0.75 + 0.35 * pebble[..., None]), sand_col)
    rough = np.where(pebble > 0.05, 0.55 + 0.2 * tone, 0.92)
    save("gravel", shade(col, h), h, rough, 8.0)


# --- grey shale, laminated and fractured -----------------------------------
def shale():
    lam = fbm(2.4, 2, 500, aniso=(0.08, 1.0), seed=31)
    base = fbm(2.0, 2, 200, seed=32)
    f1, f2, idx = worley(90, seed=33)
    cracks = np.clip((f2 - f1) / 3.0, 0, 1)
    tone = np.random.default_rng(34).random(90)[idx]
    h = 0.5 * lam + 0.2 * base + 0.3 * cracks - 0.15 * tone
    col = ramp(0.6 * lam + 0.25 * base + 0.15 * tone,
               [(0, "#2c2d2e"), (0.35, "#45474a"), (0.6, "#5d5f60"), (0.85, "#76716a"), (1, "#8a8278")])
    col *= (0.55 + 0.45 * cracks)[..., None]
    rough = 0.7 + 0.2 * base
    save("shale", shade(col, h), h, rough, 7.0)


# --- pasture ground: thatch, straw and soil beneath the grass ------------------
def pasture():
    base = fbm(2.0, 2, 300, seed=41)
    straw = fbm(2.0, 6, 512, aniso=(1.0, 0.1), seed=42)
    straw2 = fbm(2.0, 6, 512, aniso=(0.1, 1.0), seed=43)
    blades = np.clip(np.maximum(1 - np.abs(straw - 0.55) * 18, 1 - np.abs(straw2 - 0.5) * 18), 0, 1)
    soil = fbm(1.4, 20, 512, seed=44)
    h = 0.35 * base + 0.4 * blades + 0.25 * soil
    greens = ramp(base, [(0, "#4d5a2a"), (0.45, "#6d7433"), (0.7, "#8d8a45"), (1, "#a79a5c")])
    straw_col = ramp(soil, [(0, "#9a8350"), (1, "#c7b27a")])
    col = greens * (1 - blades[..., None] * 0.55) + straw_col * blades[..., None] * 0.55
    col = col * (0.8 + 0.3 * soil[..., None])
    rough = 0.88 - 0.1 * blades
    save("pasture", shade(col, h), h, rough, 5.0)


# --- water ripples normal map -------------------------------------------------
def water():
    h = 0.6 * fbm(3.2, 3, 200, seed=51) + 0.4 * fbm(2.6, 12, 400, seed=52)
    n = normal_from_height(h, 18.0)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(os.path.join(OUT, "water_normal.png"))
    print("wrote water_normal")


# --- soft puff sprite for dust / exhaust ------------------------------------------
def puff():
    S = 256
    yy, xx = np.mgrid[0:S, 0:S] / (S - 1) * 2 - 1
    r = np.sqrt(xx * xx + yy * yy)
    n = fbm(2.0, 3, 120, seed=61)[:S, :S]
    a = np.clip(1 - r, 0, 1) ** 1.6 * (0.55 + 0.6 * n)
    a = np.clip(a * 1.3, 0, 1)
    img = np.dstack([np.full((S, S), 255), np.full((S, S), 255), np.full((S, S), 255), a * 255]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, "puff.png"))
    print("wrote puff")


# --- leaf cluster sprite (alpha) for tree foliage cards ---------------------------
def leaves():
    from PIL import ImageDraw
    S = 512
    r = np.random.default_rng(71)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    greens = ["#2f3d1c", "#3c4a22", "#4a5a28", "#56662e", "#6a7236", "#3a4520", "#7a7a3a"]
    for _ in range(900):
        cx, cy = r.normal(S / 2, S / 5.2, 2)
        if (cx - S / 2) ** 2 + (cy - S / 2) ** 2 > (S * 0.46) ** 2:
            continue
        L = r.uniform(14, 30)
        a = r.uniform(0, np.pi * 2)
        w = L * r.uniform(0.35, 0.5)
        ca, sa = np.cos(a), np.sin(a)
        pts = [(cx + ca * L / 2, cy + sa * L / 2), (cx - sa * w / 2, cy + ca * w / 2),
               (cx - ca * L / 2, cy - sa * L / 2), (cx + sa * w / 2, cy - ca * w / 2)]
        c = greens[r.integers(len(greens))]
        k = 0.75 + 0.5 * (cy / S) ** 0.5 * 0 + r.uniform(-0.1, 0.25)
        rgb = tuple(int(min(255, int(c[i:i + 2], 16) * k)) for i in (1, 3, 5))
        d.polygon(pts, fill=rgb + (255,))
    img.save(os.path.join(OUT, "leaves.png"))
    print("wrote leaves")


# --- rolled straw for round hay bales -------------------------------------------
def straw():
    s = fbm(2.0, 4, 512, aniso=(0.06, 1.0), seed=81)
    s2 = fbm(1.2, 30, 512, aniso=(0.1, 1.0), seed=82)
    t = 0.6 * s + 0.4 * s2
    col = ramp(t, [(0, "#6b5732"), (0.4, "#9c8551"), (0.7, "#b99f64"), (1, "#d2bd84")])
    save("straw", col, t, 0.9 - 0.1 * s2, 5.0)


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["clay", "topsoil", "gravel", "shale", "pasture", "water", "puff", "leaves", "straw"]
    for w in which:
        globals()[w]()
