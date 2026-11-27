#!/usr/bin/env node
/**
 * 3D ASCII Christmas Tree — Truecolor Terminal Edition (High Detail · 60 FPS · 60s Loop)
 * Run directly in PowerShell / Windows Terminal:
 *   node terminal_tree.js
 */

const TAU = Math.PI * 2;
const COLS = 96;
const ROWS = 50;
const LOOP_DURATION = 60.0;
const GROUND = -1.20, Y0 = -0.92, Y1 = 1.28;
const T_GROW = [0.9, 6.4], T_GARLAND = [6.3, 8.4], T_BALLS = [8.1, 9.8];
const T_LIGHTS = [9.5, 11.8], T_GIFTS = [11.2, 13.0], T_STAR = 13.2, T_MSG = 14.4;
const MESSAGE = "M E R R Y   C H R I S T M A S   2 0 2 6";

const RAMP_NEEDLE = " .:-~=+*xv%&#W";
const RAMP_TINSEL = " ~=-+*#&@";
const RAMP_BALL   = " .o0O%#@";
const RAMP_GIFT   = " .:+*xX#%@";

function makeRng(seed = 7) {
  let a = seed >>> 0;
  return {
    random() {
      let t = (a += 0x6D2B79F5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },
    uniform(lo, hi) { return lo + (hi - lo) * this.random(); },
    normal() {
      const u = Math.max(1e-7, this.random()), v = this.random();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(TAU * v);
    }
  };
}

function envelope(y) {
  const u = Math.max(0, Math.min(1, (y - Y0) / (Y1 - Y0)));
  const tier = 1.0 + 0.055 * Math.sin(u * Math.PI * 14);
  return (0.045 + 1.12 * Math.pow(1 - u, 1.05)) * tier;
}

function growTime(y) {
  const u = Math.max(0, Math.min(1, (y - GROUND) / (Y1 - GROUND)));
  return T_GROW[0] + (T_GROW[1] - T_GROW[0]) * u;
}

function fibSphere(n) {
  const pts = [];
  const gr = (1 + Math.sqrt(5)) / 2;
  for (let k = 0; k < n; k++) {
    const i = k + 0.5;
    const phi = TAU * i / gr;
    const ct = 1 - 2 * i / n;
    const st = Math.sqrt(Math.max(0, 1 - ct * ct));
    pts.push([Math.cos(phi) * st, ct, Math.sin(phi) * st]);
  }
  return pts;
}

function buildScene() {
  const rng = makeRng(7);
  const pts = [];
  const tips = [];
  const lightT0 = [];

  const addPt = (x, y, z, nx, ny, nz, r, g, b, kind, t0, base = 1, phase = 0) => {
    const len = Math.hypot(nx, ny, nz) || 1;
    pts.push({ x, y, z, nx: nx / len, ny: ny / len, nz: nz / len, r, g, b, kind, t0, base, phase });
  };

  // 1. 28 whorls of drooping pine branches
  for (let i = 0; i < 28; i++) {
    const y = (Y0 + 0.02) + (i / 27) * ((Y1 - 0.05) - (Y0 + 0.02));
    const u = (y - Y0) / (Y1 - Y0);
    const R = envelope(y) + 0.06;
    const nb = Math.floor(7 + 14 * (1 - u));
    for (let b = 0; b < nb; b++) {
      const a = TAU * (b + 0.5 * rng.random()) / nb + i * 0.77;
      const L = R * rng.uniform(0.86, 1.12);
      const n = Math.floor(24 + 170 * L);
      const dx = Math.cos(a), dz = Math.sin(a);
      const sx = -dz, sz = dx;
      for (let k = 0; k < n; k++) {
        const s = Math.pow(rng.random(), 0.65);
        const spread = (0.030 + 0.115 * s) * rng.normal();
        const sl = s * L;
        const px = dx * sl + sx * spread;
        const pz = dz * sl + sz * spread;
        const py = y + 0.07 * sl - 0.22 * sl * sl + 0.015 * rng.normal();
        const nx = dx * 0.75 + 0.3 * rng.normal();
        const ny = 0.55 + 0.3 * rng.normal();
        const nz = dz * 0.75 + 0.3 * rng.normal();
        const ao = (0.30 + 0.70 * Math.pow(s, 1.3)) * rng.uniform(0.75, 1.12);
        const snow = s > 0.48 && rng.random() < 0.065 * s && ny > 0.45;
        const rt = rng.random();
        const cr = snow ? 0.97 : 0.08 + 0.14 * rt;
        const cg = snow ? 0.99 : 0.48 + 0.42 * rt;
        const cb = snow ? 1.00 : 0.16 + 0.16 * rt;
        addPt(px, py, pz, nx, ny, nz, cr, cg, cb, snow ? 1 : 0, growTime(y) + 0.45 * s, snow ? 1.0 : ao);
      }
      const tl = 0.94 * L;
      tips.push([dx * tl, y + 0.07 * tl - 0.22 * tl * tl, dz * tl]);
    }
  }

  // 2. Trunk
  for (let k = 0; k < 1000; k++) {
    const y = GROUND + rng.random() * (Y0 + 0.14 - GROUND);
    const phi = rng.random() * TAU;
    const nx = Math.cos(phi), nz = Math.sin(phi);
    const bark = 0.75 + 0.25 * Math.sign(Math.sin(phi * 30 + y * 5));
    addPt(nx * 0.11, y, nz * 0.11, nx, 0, nz, 0.46 * bark, 0.28 * bark, 0.15 * bark, 2, growTime(y), 1.0);
  }

  // 3. 5-strand Tinsel garland
  for (let pass = 0; pass < 4; pass++) {
    for (let k = 0; k < 1100; k++) {
      const u = k / 1100;
      const yg = Y0 + 0.14 + (Y1 - Y0 - 0.42) * u;
      const ag = TAU * 4.2 * u + 0.9;
      const swag = -0.08 * Math.abs(Math.sin(ag * 2.5));
      const rg = envelope(yg) + 0.08;
      const px = Math.cos(ag) * rg + 0.016 * rng.normal();
      const py = yg + swag + 0.016 * rng.normal();
      const pz = Math.sin(ag) * rg + 0.016 * rng.normal();
      addPt(px, py, pz, Math.cos(ag), 0.3, Math.sin(ag), 1.0, 0.82, 0.30, 3,
        T_GARLAND[0] + u * (T_GARLAND[1] - T_GARLAND[0]), 1.12, rng.random() * 10);
    }
  }

  // 4. 44 Baubles
  const sph = fibSphere(55);
  for (let k = 0; k < 44; k++) {
    const u = (k + rng.random()) / 44;
    const y = Y0 + 0.08 + u * (Y1 - Y0 - 0.34);
    const ang = k * 2.39996 + rng.uniform(-0.22, 0.22);
    const r = envelope(y) * 0.94;
    const cx = Math.cos(ang) * r, cz = Math.sin(ang) * r;
    const rad = 0.068 + 0.036 * (1 - u);
    const col = k % 5 === 4 ? [0.88, 0.93, 1.0] : (k % 2 === 0 ? [0.98, 0.20, 0.22] : [1.0, 0.78, 0.24]);
    const t0 = T_BALLS[0] + rng.random() * (T_BALLS[1] - T_BALLS[0]);
    for (const [sx, sy, sz] of sph) {
      addPt(cx + sx * rad, y + sy * rad, cz + sz * rad, sx, sy, sz, col[0], col[1], col[2], 4, t0, 1.05);
    }
  }

  // 5. 220 Fairy lights
  const bulb = fibSphere(10);
  const count = Math.min(220, tips.length);
  for (let i = 0; i < count; i++) {
    const c = tips[Math.floor((i / count) * tips.length)];
    const t0 = T_LIGHTS[0] + rng.random() * (T_LIGHTS[1] - T_LIGHTS[0]);
    lightT0.push(t0);
    const phase = rng.random() * 10;
    for (const [sx, sy, sz] of bulb) {
      addPt(c[0] + sx * 0.035, c[1] + sy * 0.035, c[2] + sz * 0.035, sx, sy, sz, 1.0, 0.88, 0.50, 5, t0, 1.25, phase);
    }
  }

  // 6. 7 Large wrapped gifts
  const gifts = [
    [0.25, 1.15, 0.38, 0.28, 0.34, 0.40, [0.98, 0.20, 0.22], [1.00, 0.82, 0.30]],
    [1.15, 1.20, 0.32, 0.36, 0.32, -0.25, [0.20, 0.52, 0.98], [0.97, 0.99, 1.00]],
    [2.05, 1.14, 0.40, 0.22, 0.32, 0.95, [1.00, 0.82, 0.30], [0.98, 0.20, 0.22]],
    [2.95, 1.20, 0.30, 0.32, 0.30, 0.20, [0.98, 0.20, 0.22], [0.16, 0.78, 0.36]],
    [3.85, 1.15, 0.36, 0.26, 0.34, 0.15, [0.16, 0.78, 0.36], [0.98, 0.20, 0.22]],
    [4.75, 1.22, 0.28, 0.34, 0.28, -0.45, [0.20, 0.52, 0.98], [1.00, 0.82, 0.30]],
    [5.60, 1.14, 0.34, 0.24, 0.30, 0.65, [0.98, 0.20, 0.22], [0.97, 0.99, 1.00]],
  ];
  for (let g = 0; g < gifts.length; g++) {
    const [a, dist, w, h, d, rot, body, rib] = gifts[g];
    const cx = Math.cos(a) * dist, cz = Math.sin(a) * dist;
    const t0 = T_GIFTS[0] + (g / gifts.length) * (T_GIFTS[1] - T_GIFTS[0]);
    const ca = Math.cos(rot), sa = Math.sin(rot);
    for (let k = 0; k < 650; k++) {
      const f = k % 5;
      const fa = rng.random() - 0.5, fb = rng.random() - 0.5;
      const lx = f === 0 ? fa * w : f === 1 ? w / 2 : f === 2 ? -w / 2 : fa * w;
      const ly = f === 0 ? h : (fb + 0.5) * h;
      const lz = f === 0 ? fb * d : f <= 2 ? fa * d : f === 3 ? d / 2 : -d / 2;
      const nx = f === 1 ? 1 : f === 2 ? -1 : 0;
      const ny = f === 0 ? 1 : 0;
      const nz = f === 3 ? 1 : f === 4 ? -1 : 0;
      const isRib = Math.abs(lx) < 0.038 || Math.abs(lz) < 0.038;
      const col = isRib ? rib : body;
      addPt(cx + lx * ca + lz * sa, GROUND + ly, cz - lx * sa + lz * ca,
        nx * ca + nz * sa, ny, -nx * sa + nz * ca, col[0], col[1], col[2], 6, t0, 1.05);
    }
  }

  return { pts, lightT0 };
}

const scene = buildScene();
let t = 0;
let lastNs = process.hrtime.bigint();
process.stdout.write("\x1b[2J\x1b[?25l");
process.on("SIGINT", () => { process.stdout.write("\x1b[?25h\x1b[0m\n"); process.exit(0); });

const chars = new Array(COLS * ROWS);
const colsR = new Uint8Array(COLS * ROWS);
const colsG = new Uint8Array(COLS * ROWS);
const colsB = new Uint8Array(COLS * ROWS);
const activeMask = new Uint8Array(COLS * ROWS);
const zbuf = new Float32Array(COLS * ROWS);

setInterval(() => {
  const nowNs = process.hrtime.bigint();
  const dt = Math.min(0.05, Number(nowNs - lastNs) / 1e9);
  lastNs = nowNs;
  t = (t + dt) % LOOP_DURATION;

  let master = 1.0;
  if (t > LOOP_DURATION - 1.5) master = Math.max(0.05, (LOOP_DURATION - t) / 1.5);
  else if (t < 0.6) master = 0.25 + 0.75 * (t / 0.6);

  activeMask.fill(0);
  zbuf.fill(1e9);

  const angle = (t * 0.34) % TAU;
  const ca = Math.cos(angle), sa = Math.sin(angle);
  const cp = Math.cos(0.15), sp = Math.sin(0.15);
  const aspect = (COLS * 9) / (ROWS * 18);

  // Dotted ground
  const horizon = Math.floor(ROWS * 0.47);
  for (let r = horizon; r < ROWS - 2; r++) {
    for (let c = (r % 2); c < COLS; c += 2) {
      const idx = r * COLS + c;
      activeMask[idx] = 1;
      chars[idx] = ".";
      const v = (r - horizon) / (ROWS - horizon);
      const b = Math.floor((48 + 70 * v) * master);
      colsR[idx] = b; colsG[idx] = Math.floor(b * 1.15); colsB[idx] = Math.floor(b * 1.45);
    }
  }

  for (let i = 0; i < scene.pts.length; i++) {
    const p = scene.pts[i];
    if (t < p.t0) continue;
    const age = t - p.t0;
    const x = p.x * ca + p.z * sa;
    const y = p.y;
    const z = -p.x * sa + p.z * ca;
    const yc = y * cp - z * sp;
    const zc = y * sp + z * cp + 3.85;
    if (zc <= 0.25) continue;

    const px = Math.floor(((x / (zc * aspect)) * 1.01 + 0.5) * COLS);
    const py = Math.floor((0.435 - (yc / zc) * 1.01) * ROWS);
    if (px < 0 || px >= COLS || py < 0 || py >= ROWS) continue;
    const idx = py * COLS + px;
    if (zc >= zbuf[idx]) continue;
    zbuf[idx] = zc;

    const nx = p.nx * ca + p.nz * sa;
    const ny = p.ny;
    const nz = -p.nx * sa + p.nz * ca;
    const diff = Math.max(0, nx * 0.48 + ny * 0.62 - nz * 0.62);
    let shade = Math.min(1.38, Math.max(0.10, (0.34 + 0.74 * diff) * p.base));
    if (p.kind === 5) shade = 1.30 * (0.85 + 0.35 * Math.sin(t * 6.5 + p.phase));
    shade *= master;

    const gf = p.kind <= 2 ? Math.pow(Math.max(0, 1 - age / 0.42), 1.8) : 0;
    activeMask[idx] = 1;
    colsR[idx] = Math.min(255, Math.floor(((p.r * (1 - gf) + gf) * shade) * 255));
    colsG[idx] = Math.min(255, Math.floor(((p.g * (1 - gf) + gf) * shade) * 255));
    colsB[idx] = Math.min(255, Math.floor(((p.b * (1 - gf) + gf) * shade) * 255));

    const ramp = p.kind === 3 ? RAMP_TINSEL : (p.kind === 4 ? RAMP_BALL : (p.kind === 6 ? RAMP_GIFT : RAMP_NEEDLE));
    const rIdx = Math.min(ramp.length - 1, Math.max(1, Math.floor((shade / 1.25) * (ramp.length - 1))));
    chars[idx] = p.kind === 5 ? "@" : ramp[rIdx];
  }

  // Top star
  if (t >= T_STAR) {
    const sy = Math.floor((0.435 - ((Y1 + 0.14) / 3.85) * 1.01) * ROWS);
    const sx = Math.floor(COLS / 2);
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        if (Math.abs(dx) + Math.abs(dy) * 2 <= 4) {
          const idx = (sy + dy) * COLS + (sx + dx);
          if (idx >= 0 && idx < activeMask.length) {
            activeMask[idx] = 1;
            chars[idx] = dx === 0 && dy === 0 ? "@" : "#";
            colsR[idx] = 255; colsG[idx] = 225; colsB[idx] = 110;
          }
        }
      }
    }
  }

  // Message banner
  if (t > T_MSG) {
    const row = ROWS - 4;
    const x0 = Math.floor((COLS - MESSAGE.length) / 2);
    const shown = Math.min(MESSAGE.length, Math.floor((t - T_MSG) * 10));
    const pal = [[250, 55, 60], [255, 205, 75], [45, 200, 95]];
    for (let i = 0; i < shown; i++) {
      const ch = MESSAGE[i];
      if (ch !== " ") {
        const idx = row * COLS + x0 + i;
        const c = pal[(Math.floor(i / 2) + Math.floor(t * 1.5)) % 3];
        activeMask[idx] = 1;
        chars[idx] = ch;
        colsR[idx] = c[0]; colsG[idx] = c[1]; colsB[idx] = c[2];
      }
    }
  }

  let out = "\x1b[H";
  for (let r = 0; r < ROWS; r++) {
    const base = r * COLS;
    for (let c = 0; c < COLS; c++) {
      const idx = base + c;
      if (activeMask[idx]) out += `\x1b[38;2;${colsR[idx]};${colsG[idx]};${colsB[idx]}m${chars[idx]}`;
      else out += " ";
    }
    out += "\x1b[0m\n";
  }
  const deg = ((angle * 180) / Math.PI).toFixed(2).padStart(6, "0");
  const lights = scene.lightT0.filter(x => t >= x).length;
  out += `\x1b[38;2;184;176;206m @nghtrung\x1b[0m   \x1b[38;2;110;118;138mrotation ${deg}°   lights ${lights}\x1b[0m`;
  process.stdout.write(out);
}, 16);
