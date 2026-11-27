"""
ASCII Christmas Tree 🎄 (@dwcminh.ascii High-Detail Edition)
Real-time 3D procedural ASCII art Christmas Tree running smoothly at 60 FPS
with a 60.0-second cycle before reset:
- 28 dense whorls of drooping pine branches, snow-dusted tips, textured trunk & dense inner cone
- 5-strand golden tinsel spiral swags, 44 specular-shaded baubles (red, gold, silver)
- 220 twinkling fairy lights + 7 large 3D wrapped gift boxes with crossed ribbons & bows
- Glowing white-to-gold 5-pointed star burst on top
- Typewriter "M E R R Y   C H R I S T M A S   2 0 2 6" cycling banner
- Live split-screen code viewer (christmas_tree.py · running · 60 fps · 60s loop)

Controls:
  Space : pause / resume
  R     : restart animation
  S     : save screenshot
  Esc   : quit
"""

import math
import time
import numpy as np
import pygame

TAU = 2 * math.pi
LOOP_DURATION = 60.0

# Larger tree geometry bounds
GROUND = -1.20
Y0 = -0.92
Y1 = 1.28

# 60-second unhurried timeline
T_GROW = (0.9, 6.4)
T_GARLAND = (6.3, 8.4)
T_BALLS = (8.1, 9.8)
T_LIGHTS = (9.5, 11.8)
T_GIFTS = (11.2, 13.0)
T_STAR = 13.2
T_MSG = 14.4

# Part categories
NEEDLE = 0
SNOW = 1
TRUNK = 2
TINSEL = 3
BALL = 4
LIGHT = 5
GIFT = 6
RIBBON = 7

# Color palette (0..1 float RGB)
WHITE = (0.97, 0.99, 1.00)
GOLD = (1.00, 0.82, 0.30)
BAUBLE_GOLD = (1.00, 0.78, 0.24)
SILVER = (0.88, 0.93, 1.00)
RED = (0.98, 0.20, 0.22)
GREEN_BOX = (0.16, 0.78, 0.36)
BLUE_BOX = (0.20, 0.52, 0.98)
WARM = (1.00, 0.88, 0.50)

MESSAGE = "M E R R Y   C H R I S T M A S   2 0 2 6"

RAMP_NEEDLE = np.frombuffer(b" .:-~=+*xv%&#W", dtype=np.uint8)
RAMP_SNOW = np.frombuffer(b" .+*#@", dtype=np.uint8)
RAMP_TRUNK = np.frombuffer(b" .:+|#H", dtype=np.uint8)
RAMP_TINSEL = np.frombuffer(b" ~=-+*#&@", dtype=np.uint8)
RAMP_BALL = np.frombuffer(b" .o0O%#@", dtype=np.uint8)
RAMP_GIFT = np.frombuffer(b" .:+*xX#%@", dtype=np.uint8)


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-8)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def envelope(y):
    u = np.clip((y - Y0) / (Y1 - Y0), 0.0, 1.0)
    tier = 1.0 + 0.055 * np.sin(u * math.pi * 14.0)
    return (0.045 + 1.12 * ((1.0 - u) ** 1.05)) * tier


def fib_sphere(n):
    i = np.arange(n, dtype=np.float64) + 0.5
    phi = TAU * i / ((1.0 + math.sqrt(5.0)) / 2.0)
    cos_t = 1.0 - 2.0 * i / n
    sin_t = np.sqrt(np.maximum(0.0, 1.0 - cos_t * cos_t))
    return np.stack([np.cos(phi) * sin_t, cos_t, np.sin(phi) * sin_t], axis=1)


class Parts:
    def __init__(self):
        self.pos = []
        self.nrm = []
        self.col = []
        self.kind = []
        self.t0 = []
        self.base = []
        self.phase = []
        self.centre = []
        self.pop = []

    def add(self, pos, nrm, col, kind, t0, base=1.0, phase=0.0, centre=None, pop=False):
        pos = np.asarray(pos, dtype=np.float32)
        m = len(pos)
        nrm = np.broadcast_to(np.asarray(nrm, dtype=np.float32), (m, 3)).copy()
        col = np.broadcast_to(np.asarray(col, dtype=np.float32), (m, 3)).copy()
        kind_arr = np.broadcast_to(np.asarray(kind, dtype=np.int32), (m,)).copy()
        t0_arr = np.broadcast_to(np.asarray(t0, dtype=np.float32), (m,)).copy()
        base_arr = np.broadcast_to(np.asarray(base, dtype=np.float32), (m,)).copy()
        phase_arr = np.broadcast_to(np.asarray(phase, dtype=np.float32), (m,)).copy()
        centre_arr = pos.copy() if centre is None else np.broadcast_to(np.asarray(centre, dtype=np.float32), (m, 3)).copy()
        pop_arr = np.full(m, bool(pop), dtype=bool)

        self.pos.append(pos)
        self.nrm.append(nrm)
        self.col.append(col)
        self.kind.append(kind_arr)
        self.t0.append(t0_arr)
        self.base.append(base_arr)
        self.phase.append(phase_arr)
        self.centre.append(centre_arr)
        self.pop.append(pop_arr)

    def finalize(self):
        self.pos = np.concatenate(self.pos, axis=0)
        self.nrm = unit(np.concatenate(self.nrm, axis=0))
        self.col = np.concatenate(self.col, axis=0)
        self.kind = np.concatenate(self.kind, axis=0)
        self.t0 = np.concatenate(self.t0, axis=0)
        self.base = np.concatenate(self.base, axis=0)
        self.phase = np.concatenate(self.phase, axis=0)
        self.centre = np.concatenate(self.centre, axis=0)
        self.pop = np.concatenate(self.pop, axis=0)
        return self


def grow_time(y):
    return T_GROW[0] + (T_GROW[1] - T_GROW[0]) * np.clip((y - GROUND) / (Y1 - GROUND), 0.0, 1.0)


def build():
    rng = np.random.default_rng(7)
    q = Parts()
    tips = []

    # 1. 28 whorls of drooping pine branches
    for i, y in enumerate(np.linspace(Y0 + 0.02, Y1 - 0.05, 28)):
        u = (y - Y0) / (Y1 - Y0)
        R = envelope(y) + 0.06
        nb = int(7 + 14 * (1 - u))
        for b in range(nb):
            a = TAU * (b + 0.5 * rng.random()) / nb + i * 0.77
            L = R * rng.uniform(0.86, 1.12)
            n = int(35 + 240 * L)
            s = rng.random(n) ** 0.65
            d = np.array([np.cos(a), 0, np.sin(a)])
            side = np.array([-np.sin(a), 0, np.cos(a)])
            spread = (0.030 + 0.115 * s) * rng.normal(0, 1, n)
            sl = s * L
            p = d * sl[:, None] + side * spread[:, None]
            p[:, 1] = y + 0.07 * sl - 0.22 * sl ** 2 + 0.015 * rng.normal(0, 1, n)
            nrm = unit(d * 0.75 + np.array([0, 0.55, 0]) + 0.3 * rng.normal(0, 1, (n, 3)))
            ao = (0.30 + 0.70 * s ** 1.3) * rng.uniform(0.75, 1.12, n)
            snow = (s > 0.48) & (rng.random(n) < 0.065 * s) & (nrm[:, 1] > 0.45)
            green = np.array([0.08, 0.48, 0.16]) + np.array([0.14, 0.42, 0.16]) * rng.random((n, 1))
            q.add(p, nrm, np.where(snow[:, None], WHITE, green), np.where(snow, SNOW, NEEDLE),
                  grow_time(y) + 0.45 * s, base=np.where(snow, 1.0, ao))
            tl = 0.94 * L
            tips.append(d * tl + [0, y + 0.07 * tl - 0.22 * tl ** 2, 0])

    # 2. Dense dark inner cone
    m = 8000
    y = Y0 + (Y1 - 0.08 - Y0) * rng.random(m)
    phi = rng.random(m) * TAU
    out = np.stack([np.cos(phi), np.full(m, 0.3), np.sin(phi)], 1)
    r = 0.64 * envelope(y)
    q.add(np.stack([np.cos(phi) * r, y, np.sin(phi) * r], 1), out, (0.08, 0.42, 0.16), NEEDLE,
          grow_time(y), base=0.72)

    # 3. Trunk
    m = 2000
    y, phi = GROUND + rng.random(m) * (Y0 + 0.14 - GROUND), rng.random(m) * TAU
    n = np.stack([np.cos(phi), np.zeros(m), np.sin(phi)], 1)
    bark = 0.75 + 0.25 * np.sign(np.sin(phi * 30 + y * 5))
    q.add(n * 0.11 + np.stack([np.zeros(m), y, np.zeros(m)], 1), n,
          np.array([0.46, 0.28, 0.15]) * bark[:, None], TRUNK, grow_time(y))

    # 4. 5-strand gold tinsel garland
    u = np.linspace(0, 1, 3200)
    turns = 4.2
    yg = Y0 + 0.14 + (Y1 - Y0 - 0.42) * u
    ag = TAU * turns * u + 0.9
    swag = -0.08 * np.abs(np.sin(ag * 2.5))
    rg = envelope(yg) + 0.08
    line = np.stack([np.cos(ag) * rg, yg + swag, np.sin(ag) * rg], 1)
    for _ in range(5):
        nrm = np.stack([np.cos(ag), np.full_like(u, 0.3), np.sin(ag)], 1) + 0.5 * rng.normal(0, 1, line.shape)
        q.add(line + 0.018 * rng.normal(0, 1, line.shape), nrm, GOLD, TINSEL,
              T_GARLAND[0] + u * (T_GARLAND[1] - T_GARLAND[0]), base=1.12, phase=rng.random(len(u)) * 10)

    # 5. 44 Baubles
    sphere = fib_sphere(130)
    for k in range(44):
        u = (k + rng.random()) / 44
        y = Y0 + 0.08 + u * (Y1 - Y0 - 0.34)
        ang = k * 2.39996 + rng.uniform(-0.22, 0.22)
        r = envelope(y) * 0.94
        c = np.array([np.cos(ang) * r, y, np.sin(ang) * r])
        rad = 0.068 + 0.036 * (1 - u)
        col = SILVER if k % 5 == 4 else (RED if k % 2 == 0 else BAUBLE_GOLD)
        q.add(c + sphere * rad, sphere, col, BALL, T_BALLS[0] + rng.random() * (T_BALLS[1] - T_BALLS[0]),
              base=1.05, centre=c, pop=True)

    # 6. 220 Fairy lights
    tips = np.array(tips)
    pick = rng.choice(len(tips), min(220, len(tips)), replace=False)
    bulb = fib_sphere(16)
    light_t0 = T_LIGHTS[0] + rng.random(len(pick)) * (T_LIGHTS[1] - T_LIGHTS[0])
    for c, t0 in zip(tips[pick], light_t0):
        rp = rng.random()
        col = WARM if rp < 0.68 else ((1.0, 0.96, 0.88) if rp < 0.85 else (RED if rp < 0.93 else (0.45, 0.90, 1.0)))
        q.add(c + bulb * 0.035, bulb, col, LIGHT, t0, base=1.25, centre=c, phase=rng.random() * 10, pop=True)

    # 7. 7 Large wrapped presents
    gifts = [
        (0.25, 1.15, 0.38, 0.28, 0.34, 0.40, RED, GOLD),
        (1.15, 1.20, 0.32, 0.36, 0.32, -0.25, BLUE_BOX, WHITE),
        (2.05, 1.14, 0.40, 0.22, 0.32, 0.95, GOLD, RED),
        (2.95, 1.20, 0.30, 0.32, 0.30, 0.20, RED, GREEN_BOX),
        (3.85, 1.15, 0.36, 0.26, 0.34, 0.15, GREEN_BOX, RED),
        (4.75, 1.22, 0.28, 0.34, 0.28, -0.45, BLUE_BOX, GOLD),
        (5.60, 1.14, 0.34, 0.24, 0.30, 0.65, RED, WHITE),
    ]
    loop = fib_sphere(80)
    for g, (a, dist, w, h, d, rot, body, rib) in enumerate(gifts):
        areas = np.array([w * d, h * d, h * d, h * w, h * w])
        m = int(5500 * areas.sum())
        face = rng.choice(5, m, p=areas / areas.sum())
        fa, fb = rng.random(m) - 0.5, rng.random(m) - 0.5
        lx = np.select([face == 0, face == 1, face == 2, face >= 3],
                       [fa * w, np.full(m, w / 2), np.full(m, -w / 2), fa * w])
        ly = np.where(face == 0, h, (fb + 0.5) * h)
        lz = np.select([face == 0, face <= 2, face == 3, face == 4],
                       [fb * d, fa * d, np.full(m, d / 2), np.full(m, -d / 2)])
        nx = np.select([face == 1, face == 2], [1.0, -1.0], default=0.0)
        ny = np.where(face == 0, 1.0, 0.0)
        nz = np.select([face == 3, face == 4], [1.0, -1.0], default=0.0)

        is_rib = (np.abs(lx) < 0.038) | (np.abs(lz) < 0.038)
        pts = np.stack([lx, ly, lz], 1)
        nrm = np.stack([nx, ny, nz], 1)
        ca, sa = math.cos(rot), math.sin(rot)
        rot_m = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
        c = np.array([math.cos(a) * dist, GROUND, math.sin(a) * dist])
        pts = pts @ rot_m.T + c
        nrm = nrm @ rot_m.T
        t0 = T_GIFTS[0] + (g / len(gifts)) * (T_GIFTS[1] - T_GIFTS[0])
        col = np.where(is_rib[:, None], rib, body)
        q.add(pts, nrm, col, np.where(is_rib, RIBBON, GIFT), t0, base=1.05, centre=c + [0, h / 2, 0], pop=True)
        bow_c = c + [0, h + 0.035, 0]
        q.add(bow_c + loop * [0.075, 0.045, 0.075], loop, rib, RIBBON, t0 + 0.12, base=1.15, centre=bow_c, pop=True)

    return q.finalize(), light_t0


def project(pts, cols, rows, aspect, angle=0.0):
    ca, sa = math.cos(angle), math.sin(angle)
    x = pts[:, 0] * ca + pts[:, 2] * sa
    y = pts[:, 1]
    z = -pts[:, 0] * sa + pts[:, 2] * ca

    pitch = 0.15
    cp, sp = math.cos(pitch), math.sin(pitch)
    yc = y * cp - z * sp
    zc = y * sp + z * cp + 3.85

    fov_half = 1.01
    sx = (x / (zc * aspect)) * fov_half
    sy = (yc / zc) * fov_half
    px = (sx + 0.5) * cols
    py = (0.435 - sy) * rows
    return px, py, zc


def put(char, col, r, c, ch, rgb, power=1.0):
    rows, cols = char.shape
    if 0 <= r < rows and 0 <= c < cols:
        char[r, c] = ord(ch) if isinstance(ch, str) else int(ch)
        col[r, c] = np.clip(np.asarray(rgb, dtype=np.float32) * power, 0.0, 1.0)


def in_poly(px, py, poly):
    res = np.zeros_like(px, dtype=bool)
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        res ^= ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-9) + x1)
    return res


def star(char, col, cx, cy, size, t, power, cell, flash=0.0):
    tint = np.array(GOLD) + (1 - np.array(GOLD)) * flash
    power = power * (1 + 1.65 * flash)
    for k in range(8):
        ang = k * TAU / 8 + 0.10 * np.sin(t * 0.7)
        if np.sin(ang) < -0.25:
            continue
        reach = size * (3.2 + 0.9 * np.sin(t * 3 + k * 1.3)) * (1.0 if k % 2 == 0 else 0.65) * (1 + 1.8 * flash)
        ch = "-/|\\" [int(round((np.degrees(ang) % 180) / 45)) % 4]
        for s in np.arange(size * 1.05, reach, 0.85):
            fade = (1.0 - s / reach) ** 1.35
            put(char, col, int(round(cy - np.sin(ang) * s / cell)), int(round(cx + np.cos(ang) * s)),
                ch, tint, power * fade * 0.90)

    poly = []
    for k in range(10):
        ang = math.pi / 2 + k * TAU / 10
        r = size if k % 2 == 0 else size * 0.43
        poly.append((cx + math.cos(ang) * r, cy - math.sin(ang) * r / cell))

    r0, r1 = max(0, int(cy - size / cell - 2)), min(char.shape[0], int(cy + size / cell + 3))
    c0, c1 = max(0, int(cx - size - 2)), min(char.shape[1], int(cx + size + 3))
    if r1 > r0 and c1 > c0:
        yy, xx = np.mgrid[r0:r1, c0:c1]
        mask = in_poly(xx.astype(np.float32), yy.astype(np.float32), poly)
        dist = np.hypot(xx - cx, (yy - cy) * cell) / max(size, 1e-4)
        for ry, rx in zip(*np.where(mask)):
            d = dist[ry, rx]
            ch = "@" if d < 0.35 else ("#" if d < 0.72 else "*")
            c_tint = WHITE if d < 0.32 else tint
            put(char, col, r0 + ry, c0 + rx, ch, c_tint, min(1.35, power * (1.20 - 0.25 * d)))


class Scene:
    def __init__(self):
        self.parts, self.light_t0 = build()
        rng = np.random.default_rng(11)
        self.bg_stars = np.column_stack([
            rng.integers(0, COLS, 165),
            rng.integers(0, int(ROWS * 0.47), 165),
            rng.random(165) * TAU,
            rng.choice([ord('.'), ord('+'), ord('*')], 165, p=[0.6, 0.28, 0.12])
        ])
        self.snow_p = np.column_stack([
            rng.uniform(0, COLS, 120),
            rng.uniform(0, ROWS, 120),
            rng.uniform(3.2, 8.4, 120),
            rng.uniform(0, TAU, 120)
        ])

    def render_frame(self, t, cols, rows, cw, ch):
        char = np.zeros((rows, cols), dtype=np.int32)
        col = np.zeros((rows, cols, 3), dtype=np.float32)

        master = 1.0
        if t > LOOP_DURATION - 1.5:
            master = max(0.05, (LOOP_DURATION - t) / 1.5)
        elif t < 0.6:
            master = 0.25 + 0.75 * (t / 0.6)

        aspect = (cols * cw) / (rows * ch)
        cell = ch / cw
        angle = (t * 0.34) % TAU
        deg = math.degrees(angle) % 360.0

        # 1. Twinkling sky stars
        for sx, sy, sp, sch in self.bg_stars:
            tw = (0.35 + 0.50 * math.sin(t * 2.2 + sp)) * master
            if tw > 0.22:
                put(char, col, int(sy), int(sx), int(sch), (0.78, 0.85, 0.98), tw)

        # 2. Perspective dotted ground grid
        horizon = int(rows * 0.47)
        for r in range(horizon, rows):
            v = (r - horizon) / (rows - horizon)
            step = 1 if v > 0.55 else 2
            fade = (0.16 + 0.32 * v) * master
            for c in range(r % 2, cols, step):
                put(char, col, r, c, ".", (0.44, 0.52, 0.72), fade)

        # 3. Falling snow
        for sx, sy, spd, sp in self.snow_p:
            y = int((sy + t * spd) % rows)
            x = int((sx + math.sin(t * 1.3 + sp) * 2.4) % cols)
            ch_s = "*" if spd > 6.8 else ("+" if spd > 5.0 else ".")
            put(char, col, y, x, ch_s, (0.88, 0.93, 1.0), 0.62 * master)

        # 4. Active 3D tree particles
        q = self.parts
        active = t >= q.t0
        if np.any(active):
            idx = np.where(active)[0]
            age = t - q.t0[idx]
            pos = q.pos[idx].copy()
            nrm = q.nrm[idx]
            pcol = q.col[idx].copy()
            kind = q.kind[idx]
            base = q.base[idx]
            phase = q.phase[idx]

            pop_mask = q.pop[idx] & (age < 0.40)
            if np.any(pop_mask):
                u_pop = smooth(age[pop_mask] / 0.40)[:, None]
                c_pop = q.centre[idx[pop_mask]]
                pos[pop_mask] = c_pop + (pos[pop_mask] - c_pop) * u_pop

            ca, sa = math.cos(angle), math.sin(angle)
            nx = nrm[:, 0] * ca + nrm[:, 2] * sa
            ny = nrm[:, 1]
            nz = -nrm[:, 0] * sa + nrm[:, 2] * ca

            diff = np.maximum(0.0, nx * 0.48 + ny * 0.62 - nz * 0.62)
            rim = np.maximum(0.0, 1.0 - np.abs(nz)) ** 2
            shade = np.clip((0.34 + 0.74 * diff + 0.22 * rim) * base, 0.10, 1.38)

            grow_flash = np.clip(1.0 - age / 0.42, 0.0, 1.0) ** 1.8
            is_tree = kind <= TRUNK
            gf = np.where(is_tree, grow_flash, 0.0)
            pcol = pcol * (1.0 - gf[:, None]) + np.array(WHITE, dtype=np.float32) * gf[:, None]
            shade = np.where(gf > 0.1, np.maximum(shade, 0.98 * gf), shade)

            is_ball = kind == BALL
            if np.any(is_ball):
                spec = np.where(is_ball, np.maximum(0.0, nx * 0.42 + ny * 0.65 - nz * 0.63) ** 12, 0.0)
                mask_s = spec > 0.35
                pcol = np.where(mask_s[:, None], pcol * (1.0 - spec[:, None]) + np.array(WHITE, dtype=np.float32) * spec[:, None], pcol)
                shade = np.where(mask_s, np.maximum(shade, 1.25), shade)

            shade = np.where(kind == LIGHT, 1.30 * (0.85 + 0.35 * np.sin(t * 6.5 + phase)), shade)
            shade = np.where(kind == TINSEL, shade * (0.84 + 0.32 * np.sin(t * 5.0 + phase)), shade)
            shade *= master

            px, py, zc = project(pos, cols, rows, aspect, angle=angle)
            ix = np.floor(px).astype(np.int32)
            iy = np.floor(py).astype(np.int32)
            valid = (ix >= 0) & (ix < cols) & (iy >= 0) & (iy < rows) & (zc > 0.25)

            ix, iy, zc = ix[valid], iy[valid], zc[valid]
            shade, pcol, kind = shade[valid], pcol[valid], kind[valid]

            order = np.argsort(-zc)
            ix, iy = ix[order], iy[order]
            shade, pcol, kind = shade[order], pcol[order], kind[order]

            ch_codes = RAMP_NEEDLE[np.clip((shade * (len(RAMP_NEEDLE) - 1) / 1.25).astype(np.int32), 1, len(RAMP_NEEDLE) - 1)].astype(np.int32)
            for k_val, ramp in ((SNOW, RAMP_SNOW), (TRUNK, RAMP_TRUNK), (TINSEL, RAMP_TINSEL), (BALL, RAMP_BALL), (GIFT, RAMP_GIFT), (RIBBON, RAMP_GIFT)):
                m_k = kind == k_val
                if np.any(m_k):
                    r_i = np.clip((shade[m_k] * (len(ramp) - 1) / 1.25).astype(np.int32), 1, len(ramp) - 1)
                    ch_codes[m_k] = ramp[r_i]
            ch_codes = np.where(kind == LIGHT, ord('@'), ch_codes)

            char[iy, ix] = ch_codes
            col[iy, ix] = np.clip(pcol * shade[:, None], 0.0, 1.0)

        # 5. Glowing top star
        if t >= T_STAR:
            on = float(smooth((t - T_STAR) / 0.35))
            flash = float(np.clip(1 - (t - T_STAR) / 1.1, 0, 1) ** 2)
            tx, ty, _ = project(np.array([[0.0, Y1 + 0.14, 0.0]]), cols, rows, aspect, angle=angle)
            star(char, col, int(tx[0]), int(ty[0]), (2.2 + 2.4 * on) * (1 + 0.05 * np.sin(t * 4)),
                 t, 0.98 * on * master, cell, flash=flash)

        # 6. Typewriter message banner
        if t > T_MSG:
            row, x0 = rows - 7, (cols - len(MESSAGE)) // 2
            shown = min(len(MESSAGE), int((t - T_MSG) * 10))
            char[row - 1:row + 2, max(x0 - 3, 0):x0 + shown + 3] = 0
            for i, ch_m in enumerate(MESSAGE[:shown]):
                if ch_m != " ":
                    tint = (RED, GOLD, GREEN_BOX)[(i // 2 + int(t * 1.5)) % 3]
                    put(char, col, row, x0 + i, ch_m, tint, (0.88 + 0.25 * np.sin(t * 5 + i)) * master)

        return char, col, {
            "t": t,
            "rotation": deg,
            "lights": int((t >= self.light_t0).sum()),
            "letters": int((char > 0).sum()),
        }


TITLE = "ASCII Christmas Tree"
CW, CH, FONT_PX = 9, 14, 15
COLS, ROWS = 96, 78
W, H = COLS * CW, ROWS * CH
MONO = "consolas,menlo,dejavusansmono,couriernew,monospace"
HINT = "Space pause · R restart · S screenshot · Esc quit"
DIM, ACCENT, SIGN = (110, 118, 138), (255, 196, 90), (184, 176, 206)


class Renderer:
    def __init__(self, cols=COLS, rows=ROWS, cw=CW, ch=CH, font_px=FONT_PX, hud_px=13):
        self.cols, self.rows, self.cw, self.ch = cols, rows, cw, ch
        self.w, self.h = cols * cw, rows * ch
        font = pygame.font.SysFont(MONO, font_px, bold=True)
        self.hud_font = pygame.font.SysFont(MONO, hud_px)
        self.code_font = pygame.font.SysFont(MONO, 12)
        atlas = []
        for code in range(32, 127):
            s = pygame.Surface((cw, ch))
            g = font.render(chr(code), True, (255, 255, 255))
            s.blit(g, ((cw - g.get_width()) // 2, (ch - g.get_height()) // 2))
            atlas.append(pygame.surfarray.array3d(s).transpose(1, 0, 2))
        self.atlas = np.stack(atlas).astype(np.float32) / 255.0

        try:
            with open(__file__, "r", encoding="utf-8") as f:
                self.source_lines = [line.rstrip("\n") for line in f.readlines()]
        except Exception:
            self.source_lines = ["# christmas_tree.py"]

    def draw(self, screen, char, col, info, code_h=220):
        idx = np.clip(char - 32, 0, 94)
        glyphs = self.atlas[idx]
        colored = (glyphs * (col[:, :, None, None, :] * 255.0)).astype(np.uint8)
        img = colored.transpose(0, 2, 1, 3, 4).reshape(self.h, self.w, 3)

        bg = np.array([7, 9, 15], dtype=np.uint8)
        mask = img.max(axis=-1, keepdims=True) == 0
        img = np.where(mask, bg, np.maximum(img, bg))

        surf = pygame.surfarray.make_surface(img.transpose(1, 0, 2))
        screen.blit(surf, (0, 0))

        t_surf = self.hud_font.render(f"t {info['t']:05.2f}s / 60.0s", True, ACCENT)
        screen.blit(t_surf, (self.w - t_surf.get_width() - 14, 10))

        sig = self.hud_font.render("@dwcminh.ascii", True, SIGN)
        rot = self.hud_font.render(f"rotation {info['rotation']:06.2f}°     lights {info['lights']}", True, DIM)
        let = self.hud_font.render(f"letters {info['letters']:,}", True, DIM)
        screen.blit(sig, (14, self.h - 62))
        screen.blit(rot, (14, self.h - 42))
        screen.blit(let, (14, self.h - 24))

        if code_h > 0:
            y0 = self.h
            pygame.draw.rect(screen, (13, 16, 23), (0, y0, self.w, code_h))
            pygame.draw.rect(screen, (20, 24, 34), (0, y0, self.w, 28))
            pygame.draw.line(screen, (38, 44, 58), (0, y0), (self.w, y0), 1)
            screen.blit(self.hud_font.render("christmas_tree.py", True, (210, 216, 228)), (14, y0 + 6))
            st_surf = self.hud_font.render("running · 60 fps · 60s loop", True, ACCENT)
            screen.blit(st_surf, (self.w - st_surf.get_width() - 14, y0 + 6))

            total = max(1, len(self.source_lines) - 11)
            scroll = int(((info["t"] % LOOP_DURATION) / LOOP_DURATION) * total)
            hi_row = scroll + 5
            for i in range(11):
                ln_idx = scroll + i
                if ln_idx >= len(self.source_lines):
                    break
                ly = y0 + 34 + i * 16
                if ln_idx == hi_row:
                    pygame.draw.rect(screen, (26, 32, 46), (0, ly - 1, self.w, 16))
                screen.blit(self.code_font.render(f"{ln_idx + 1:3d}", True, (76, 84, 102)), (10, ly))
                raw = self.source_lines[ln_idx][:96]
                col_c = (118, 132, 156) if raw.lstrip().startswith("#") else (
                    (198, 140, 255) if any(raw.lstrip().startswith(k) for k in ("def ", "class ", "for ", "if ", "return "))
                    else (216, 222, 233)
                )
                screen.blit(self.code_font.render(raw, True, col_c), (46, ly))


def main():
    pygame.init()
    code_h = 220
    screen = pygame.display.set_mode((W, H + code_h))
    pygame.display.set_caption(f"{TITLE}  —  {HINT}")
    clock = pygame.time.Clock()

    scene = Scene()
    renderer = Renderer()

    t = 0.0
    paused = False
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    paused = not paused
                elif ev.key == pygame.K_r:
                    t = 0.0
                elif ev.key == pygame.K_s:
                    fname = f"christmas_tree_{int(time.time())}.png"
                    pygame.image.save(screen, fname)
                    print(f"Saved screenshot: {fname}")

        if not paused:
            t += dt
            if t >= LOOP_DURATION:
                t -= LOOP_DURATION

        char, col, info = scene.render_frame(t, COLS, ROWS, CW, CH)
        renderer.draw(screen, char, col, info, code_h=code_h)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
